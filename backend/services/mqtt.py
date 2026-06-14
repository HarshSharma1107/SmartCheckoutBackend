from uuid import UUID


def device_command_topic(device_id: UUID | str) -> str:
    return f"ekart/device/{device_id}/commands"


def device_status_topic(device_id: UUID | str) -> str:
    return f"ekart/device/{device_id}/status"


def config_invalidation_payload() -> dict[str, str]:
    return {"action": "INVALIDATE_CONFIG"}

