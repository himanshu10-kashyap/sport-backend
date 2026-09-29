import io
import logging
from PIL import Image

logger = logging.getLogger(__name__)

_model = None
_transforms = None
_class_names = None

def get_model():
    """
    Initializes and caches the NSFW detection model globally so it's loaded only once.
    Requires torch and timm installed.
    """
    global _model, _transforms, _class_names
    if _model is None:
        try:
            import torch
            import timm
            logger.info("Loading Marqo/nsfw-image-detection-384 model...")
            # We use eval mode and map to CPU (or GPU if available)
            _model = timm.create_model("hf_hub:Marqo/nsfw-image-detection-384", pretrained=True)
            _model.eval()
            
            data_config = timm.data.resolve_model_data_config(_model)
            _transforms = timm.data.create_transform(**data_config, is_training=False)
            _class_names = _model.pretrained_cfg.get("label_names", ["nsfw", "sfw"])
            logger.info("NSFW model loaded successfully.")
        except ImportError:
            logger.error("torch or timm not installed. Cannot load NSFW model.")
            return None, None, None
        except Exception as e:
            logger.error(f"Failed to load NSFW model: {e}")
            return None, None, None
            
    return _model, _transforms, _class_names

def is_nsfw_image(image_bytes: bytes, threshold: float = 0.5) -> bool:
    """
    Detects if an image contains NSFW content.
    Returns True if the probability of the image being NSFW is > threshold.
    """
    model, transforms, class_names = get_model()
    if model is None:
        # If the model failed to load, fallback to False to allow uploads, 
        # or True to block all (safe default is False so app doesn't break).
        return False

    try:
        import torch
        img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        
        with torch.no_grad():
            tensor = transforms(img).unsqueeze(0)
            output = model(tensor)
            probabilities = output.softmax(dim=-1).cpu()[0]
            
        nsfw_index = next((i for i, name in enumerate(class_names) if name.lower() == "nsfw"), None)
        
        if nsfw_index is not None:
            is_nsfw = probabilities[nsfw_index].item() > threshold
        else:
            # Fallback if labels are missing/different: assume index 0 or use argmax logic
            # Typically class 0 is safe, 1 is unsafe or vice versa. We rely on standard label naming.
            pred_class = class_names[probabilities.argmax()]
            is_nsfw = (pred_class.lower() == "nsfw")
            
        if is_nsfw:
            logger.warning("NSFW content detected in upload.")
            
        return is_nsfw
        
    except Exception as e:
        logger.error(f"Error processing image for NSFW detection: {e}")
        return False
