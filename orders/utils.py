import re

def normalize_phone(phone: str) -> str:
    if not phone:
        return ""

    phone = re.sub(r"\D", "", phone)

    if phone.startswith("57") and len(phone) == 12:
        phone = phone[2:]

    return phone