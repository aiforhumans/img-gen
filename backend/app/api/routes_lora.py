from fastapi import APIRouter
from backend.app.lora.lora_scanner import lora_scanner

router = APIRouter(prefix="/api/loras", tags=["lora"])

@router.get("")
async def get_loras():
    """Lists all detected LoRA modules across configured directories."""
    loras = lora_scanner.scan_folders()
    return {"loras": loras}

@router.post("/scan")
async def rescan_loras():
    """Forces an immediate rescan of all configured LoRA directories."""
    loras = lora_scanner.scan_folders()
    return {"success": True, "count": len(loras), "loras": loras}
