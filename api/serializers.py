from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework import serializers

from businesses.models import Business
from menu.models import MenuCategory, MenuItem
from orders.models import Order, OrderItem, CustomerProfile
from orders.utils import normalize_phone
from users.models import AppCustomer


class BusinessSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()
    cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Business
        fields = [
            "id",
            "name",
            "slug",
            "business_type",
            "menu_mode",
            "zone",
            "address",
            "phone",
            "whatsapp",
            "instagram",
            "description",
            "avg_prep_time",
            "logo_url",
            "cover_image_url",
            "is_accepting_orders",
        ]

    def get_logo_url(self, obj):
        request = self.context.get("request")
        if obj.logo:
            if request:
                return request.build_absolute_uri(obj.logo.url)
            return obj.logo.url
        return None

    def get_cover_image_url(self, obj):
        request = self.context.get("request")
        if obj.cover_image:
            if request:
                return request.build_absolute_uri(obj.cover_image.url)
            return obj.cover_image.url
        return None


class MenuCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuCategory
        fields = ["id", "name", "order"]


class MenuItemSerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()
    category_id = serializers.IntegerField(source="category.id", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = MenuItem
        fields = [
            "id",
            "name",
            "description",
            "price",
            "photo_url",
            "is_available",
            "order",
            "category_id",
            "category_name",
        ]

    def get_photo_url(self, obj):
        request = self.context.get("request")
        if obj.photo:
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        return None


class BusinessDetailSerializer(serializers.Serializer):
    business = BusinessSerializer()
    categories = MenuCategorySerializer(many=True)
    items = MenuItemSerializer(many=True)


class RegisterCustomerSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=120)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=40)
    password = serializers.CharField(write_only=True, min_length=6)

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Ya existe una cuenta con ese correo.")
        return email

    def validate_phone(self, value):
        phone = normalize_phone(value)
        if not phone:
            raise serializers.ValidationError("Debes enviar un teléfono válido.")
        if AppCustomer.objects.filter(phone=phone).exists():
            raise serializers.ValidationError("Ya existe una cuenta con ese teléfono.")
        return phone

    def create(self, validated_data):
        email = validated_data["email"]
        full_name = validated_data["full_name"].strip()
        phone = validated_data["phone"]
        password = validated_data["password"]

        username_base = email.split("@")[0]
        username = username_base
        suffix = 1

        while User.objects.filter(username=username).exists():
            username = f"{username_base}{suffix}"
            suffix += 1

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=full_name,
        )

        app_customer = AppCustomer.objects.create(
            user=user,
            phone=phone,
            full_name=full_name,
        )

        return app_customer


class LoginCustomerSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs["email"].strip().lower()
        password = attrs["password"]

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise serializers.ValidationError("Credenciales inválidas.")

        auth_user = authenticate(username=user.username, password=password)
        if not auth_user:
            raise serializers.ValidationError("Credenciales inválidas.")

        if not hasattr(auth_user, "app_customer"):
            raise serializers.ValidationError("Esta cuenta no tiene perfil de cliente.")

        attrs["user"] = auth_user
        attrs["app_customer"] = auth_user.app_customer
        return attrs


class AppCustomerSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = AppCustomer
        fields = [
            "id",
            "full_name",
            "phone",
            "default_address",
            "email",
        ]


class CreateOrderItemInputSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class CreateOrderSerializer(serializers.Serializer):
    business_slug = serializers.CharField()
    customer_name = serializers.CharField(max_length=120)
    customer_phone = serializers.CharField(max_length=40)
    customer_address = serializers.CharField(max_length=220)
    notes = serializers.CharField(required=False, allow_blank=True)
    payment_method = serializers.ChoiceField(
        choices=[Order.PAYMENT_TRANSFER, Order.PAYMENT_CASH],
        default=Order.PAYMENT_TRANSFER,
    )
    items = CreateOrderItemInputSerializer(many=True)

    def validate(self, attrs):
        business_slug = attrs["business_slug"]
        items_data = attrs["items"]

        try:
            business = Business.objects.get(
                slug=business_slug,
                is_active=True,
                is_approved=True,
            )
        except Business.DoesNotExist:
            raise serializers.ValidationError("Negocio no encontrado.")

        if not items_data:
            raise serializers.ValidationError("Debes enviar al menos un producto.")

        customer_phone = normalize_phone(attrs.get("customer_phone"))
        if not customer_phone:
            raise serializers.ValidationError("Debes enviar un teléfono válido.")

        attrs["customer_phone"] = customer_phone

        item_ids = [item["item_id"] for item in items_data]
        menu_items = MenuItem.objects.filter(
            business=business,
            id__in=item_ids,
            is_available=True,
        )

        menu_items_map = {item.id: item for item in menu_items}

        validated_items = []
        total = 0

        for row in items_data:
            item_id = row["item_id"]
            quantity = row["quantity"]

            menu_item = menu_items_map.get(item_id)
            if not menu_item:
                raise serializers.ValidationError(
                    f"El producto con id {item_id} no existe o no está disponible."
                )

            price = int(menu_item.price)
            subtotal = price * quantity
            total += subtotal

            validated_items.append({
                "menu_item": menu_item,
                "quantity": quantity,
                "price": price,
                "subtotal": subtotal,
            })

        attrs["business_obj"] = business
        attrs["validated_items"] = validated_items
        attrs["calculated_total"] = total
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        business = validated_data["business_obj"]
        notes = validated_data.get("notes", "")
        payment_method = validated_data["payment_method"]
        total = validated_data["calculated_total"]
        validated_items = validated_data["validated_items"]

        customer_phone = validated_data["customer_phone"]
        customer_name = validated_data["customer_name"].strip()
        customer_address = validated_data["customer_address"].strip()

        customer, _ = CustomerProfile.objects.get_or_create(
            phone=customer_phone,
            defaults={"name": customer_name},
        )

        if customer_name and customer.name != customer_name:
            customer.name = customer_name
            customer.save(update_fields=["name", "updated_at"])

        allowed_payment_methods = [Order.PAYMENT_TRANSFER]
        if customer.can_pay_cash():
            allowed_payment_methods.append(Order.PAYMENT_CASH)

        if payment_method not in allowed_payment_methods:
            payment_method = Order.PAYMENT_TRANSFER

        app_customer = None
        if request and request.user.is_authenticated and hasattr(request.user, "app_customer"):
            app_customer = request.user.app_customer

        order = Order.objects.create(
            business=business,
            customer=customer,
            app_customer=app_customer,
            buyer_name=customer_name,
            buyer_phone=customer_phone,
            buyer_address=customer_address,
            buyer_notes=notes.strip(),
            payment_method=payment_method,
            total=total,
        )

        order_items = []
        for row in validated_items:
            menu_item = row["menu_item"]
            quantity = row["quantity"]
            price = row["price"]

            order_items.append(
                OrderItem(
                    order=order,
                    name=menu_item.name,
                    qty=quantity,
                    price=price,
                    subtotal=row["subtotal"],
                )
            )

        OrderItem.objects.bulk_create(order_items)

        customer.successful_orders += 1
        if customer_name and not customer.name:
            customer.name = customer_name
            customer.save(update_fields=["successful_orders", "name", "updated_at"])
        else:
            customer.save(update_fields=["successful_orders", "updated_at"])

        if app_customer:
            changed = False
            if app_customer.full_name != customer_name and customer_name:
                app_customer.full_name = customer_name
                changed = True
            if app_customer.phone != customer_phone and customer_phone:
                app_customer.phone = customer_phone
                changed = True
            if customer_address and not app_customer.default_address:
                app_customer.default_address = customer_address
                changed = True
            if changed:
                app_customer.save()

        return order


class PaymentOptionsSerializer(serializers.Serializer):
    business_slug = serializers.CharField()
    customer_phone = serializers.CharField(max_length=40)

    def validate(self, attrs):
        business_slug = attrs["business_slug"]

        try:
            business = Business.objects.get(
                slug=business_slug,
                is_active=True,
                is_approved=True,
            )
        except Business.DoesNotExist:
            raise serializers.ValidationError("Negocio no encontrado.")

        customer_phone = normalize_phone(attrs.get("customer_phone"))
        if not customer_phone:
            raise serializers.ValidationError("Debes enviar un teléfono válido.")

        attrs["business_obj"] = business
        attrs["customer_phone"] = customer_phone
        return attrs


class OrderListSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(source="business.name", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "number",
            "created_at",
            "status",
            "payment_method",
            "total",
            "business_name",
        ]


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["id", "name", "qty", "price", "subtotal"]


class OrderDetailSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(source="business.name", read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "number",
            "created_at",
            "status",
            "payment_method",
            "total",
            "business_name",
            "buyer_name",
            "buyer_phone",
            "buyer_address",
            "buyer_notes",
            "items",
        ]