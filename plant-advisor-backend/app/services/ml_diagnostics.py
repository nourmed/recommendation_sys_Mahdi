import io
import torch
import torchvision.transforms as transforms
from PIL import Image
from ultralytics import YOLO
import sys

# We need timm installed for the ViT model to load correctly
try:
    import timm
except ImportError:
    print("Warning: timm is not installed, but required for the ViT model.")

class PlantDiagnosticsService:
    def __init__(self):
        self.yolo_model_path = "app/ml_models/yolo_trained_model.pt"
        self.vit_model_path = "app/ml_models/vit_best_model.pth"
        
        self.yolo_model = None
        self.vit_model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # ViT transforms (standard ImageNet/timm transforms)
        self.vit_transforms = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        # User provided class names for the ViT model
        self.vit_class_names = [
            'Apple___Apple_scab_leaf', 'Apple___Black_rot_leaf', 'Apple___Cedar_apple_rust_leaf', 'Apple_black_rot_spot_shrivel_leaf', 'Apple_cedar_fungal_tubes_leaf', 'Apple_healthy_leaf', 'Apple_scab_leaf', 'Black_pepper__blight_powdery_leaf', 'Black_pepper_healthy_leaf', 'Black_pepper_mottle_virus_leaf',
            'Blueberry___healthy_leaf', 'Cashew_anthracnose_leaf', 'Cashew_healthy_leaf', 'Cashew_mining_blisters_leaf', 'Cashew_red_rust_spots_leaf', 'Cassava_bacterial_blight_leaf', 'Cassava_brown_spot_leaf', 'Cassava_green_mite_damage_leaf', 'Cassava_healthy_leaf', 'Cassava_mosaic_virus_leaf',
            'Cherry_(including_sour)___Powdery_mildew_leaf', 'Cherry_(including_sour)___healthy_leaf', 'Cherry_healthy_leaf', 'Cherry_powdery_mildew_leaf', 'Coffee_cerscospora_brown_spots_leaf', 'Coffee_healthy_leaf', 'Coffee_miner_damage_leaf', 'Coffee_phoma_dark_patches_leaf', 'Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot_leaf', 'Corn_(maize)___Common_rust_leaf',
            'Corn_(maize)___Northern_Leaf_Blight_leaf', 'Corn_(maize)___healthy_leaf', 'Cucumber_anthracnose_dark_spots_leaf', 'Cucumber_bacterial_wilt_leaf', 'Cucumber_downy_mildew_leaf', 'Cucumber_healthy_leaf', 'Grape___Black_rot_leaf', 'Grape___Esca_(Black_Measles)_leaf', 'Grape___Leaf_blight_(Isariopsis_Leaf_Spot)_leaf', 'Grape_black_rot_blotches_leaf',
            'Grape_brown_spot_leaf', 'Grape_esca_chlorotic_areas_leaf', 'Grape_healthy_leaf', 'Grape_mites_white_patches_leaf', 'Grape_powdery_mildew_shothole_leaf', 'Grape_purple_spots_leaf', 'Maize_healthy_leaf', 'Maize_northern_blight_lesions_leaf', 'Mango_anthracnose_dark_spots_leaf', 'Mango_bacterial_canker_leaf',
            'Mango_cutting_weevil_leaf', 'Mango_die_back_leaf', 'Mango_gall_midge_leaf', 'Mango_healthy_leaf', 'Mango_powdery_mildew_leaf', 'Mango_sooty_mould_leaf', 'Orange___Haunglongbing_(Citrus_greening)_leaf', 'Orange_haunglongbing_yellow_mottle_leaf', 'Peach___Bacterial_spot_leaf', 'Peach_bacterial_spot_shothole_leaf',
            'Peach_healthy_leaf', 'Pepper,_bell___Bacterial_spot_leaf', 'Pepper,_bell___healthy_leaf', 'Pepper__bell___Bacterial_spot_leaf', 'Pepper__bell___healthy_leaf', 'Pepper_bacterial_spot_leaf', 'Pepper_bell_leaf_spot_leaf', 'Pepper_healthy_leaf', 'Potato___Early_blight_leaf', 'Potato___Late_blight_leaf',
            'Potato_early_blight_dark_spots_leaf', 'Potato_healthy_leaf', 'Potato_late_blight_yellow_rings_leaf', 'Raspberry_healthy_leaf', 'Soybean_healthy_leaf', 'Squash_powdery_mildew_leaf', 'Strawberry___Leaf_scorch_leaf', 'Strawberry_healthy_leaf', 'Strawberry_leaf_scorch_dark_spots_leaf', 'Sugarcane_banded_chlorosis_leaf',
            'Sugarcane_brown_rust_leaf', 'Sugarcane_brown_spot_leaf', 'Sugarcane_dried_leaf', 'Sugarcane_grassy_shoot_leaf', 'Sugarcane_healthy_leaf', 'Sugarcane_mosaic_virus_leaf', 'Sugarcane_pokkah_boeng_leaf', 'Sugarcane_sett_rot_leaf', 'Sugarcane_smut_leaf', 'Sugarcane_yellow_leaf',
            'Tea_blight_brown_patches_leaf', 'Tea_healthy_leaf', 'Tea_red_scab_spots_leaf', 'Tea_red_spot_leaf', 'Tomato_Bacterial_spot_leaf', 'Tomato_Early_blight_leaf', 'Tomato_Late_blight_leaf', 'Tomato_Leaf_Mold_leaf', 'Tomato_Septoria_leaf_spot_leaf', 'Tomato_Spider_mites_Two_spotted_spider_mite_leaf',
            'Tomato__Target_Spot_leaf', 'Tomato__Tomato_YellowLeaf__Curl_Virus_leaf', 'Tomato__Tomato_mosaic_virus_leaf', 'Tomato___Spider_mites Two-spotted_spider_mite_leaf', 'Tomato___Tomato_Yellow_Leaf_Curl_Virus_leaf', 'Tomato___Tomato_mosaic_virus_leaf', 'Tomato_early_blight_target_spots_leaf', 'Tomato_healthy_leaf', 'Tomato_late_blight_lesions_leaf', 'Tomato_leaf_mold_spots_leaf',
            'Tomato_mosaic_virus_leaf', 'Tomato_septoria_spot_leaf', 'Tomato_target_spot_leaf', 'Tomato_two_spotted_mite_leaf', 'Tomato_verticillium_wilt_leaf', 'Tomato_yellow_curl_leaf'
        ]
        
        # User provided class names for the YOLO model (30 classes)
        self.yolo_class_names = [
            'Apple Scab Leaf', 'Apple leaf', 'Apple rust leaf', 'Bell_pepper leaf', 'Bell_pepper leaf spot', 'Blueberry leaf', 'Cherry leaf', 'Corn Gray leaf spot', 'Corn leaf blight', 'Corn rust leaf',
            'Peach leaf', 'Potato leaf', 'Potato leaf early blight', 'Potato leaf late blight', 'Raspberry leaf', 'Soyabean leaf', 'Soybean leaf', 'Squash Powdery mildew leaf', 'Strawberry leaf', 'Tomato Early blight leaf',
            'Tomato Septoria leaf spot', 'Tomato leaf', 'Tomato leaf bacterial spot', 'Tomato leaf late blight', 'Tomato leaf mosaic virus', 'Tomato leaf yellow virus', 'Tomato mold leaf', 'Tomato two spotted spider mites leaf', 'grape leaf', 'grape leaf black rot'
        ]
        
        self._load_models()

    def _load_models(self):
        """Loads the models into memory."""
        try:
            print(f"Loading YOLO model from {self.yolo_model_path}...")
            self.yolo_model = YOLO(self.yolo_model_path)
        except Exception as e:
            print(f"Failed to load YOLO model: {e}")

        try:
            print(f"Loading ViT model from {self.vit_model_path}...")
            # weights_only=False is required because it's a full model object, not just a state_dict
            self.vit_model = torch.load(self.vit_model_path, map_location=self.device, weights_only=False)
            self.vit_model.eval()
        except Exception as e:
            print(f"Failed to load ViT model: {e}")

    def diagnose_image(self, file_bytes: bytes) -> dict:
        """
        Runs the full diagnostic pipeline:
        1. YOLO detects the leaf and bounding boxes.
        2. Cropped leaf is passed to ViT for classification.
        """
        if not self.yolo_model or not self.vit_model:
            return {
                "status": "error",
                "message": "Models are not loaded correctly on the server."
            }

        try:
            # 1. Open the image
            img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            
            # 2. Run YOLO for leaf detection
            results = self.yolo_model(img)
            
            # Get the first bounding box (assume largest/best confidence leaf)
            # YOLOv8 returns a list of Results objects
            has_detection = len(results) > 0 and len(results[0].boxes) > 0
            
            if has_detection:
                box_data = results[0].boxes[0]
                box = box_data.xyxy[0].cpu().numpy()  # [x1, y1, x2, y2]
                yolo_confidence = float(box_data.conf[0].cpu().numpy())
                yolo_class_idx = int(box_data.cls[0].cpu().numpy())
                
                if 0 <= yolo_class_idx < len(self.yolo_class_names):
                    yolo_class_name = self.yolo_class_names[yolo_class_idx].replace("_", " ")
                else:
                    # Fallback to model's built in names if indices don't match or the internal names
                    yolo_class_name = results[0].names.get(yolo_class_idx, f"Object {yolo_class_idx}")
                
                # Crop the image using the bounding box
                leaf_crop = img.crop((box[0], box[1], box[2], box[3]))
            else:
                # Fallback: if YOLO can't find a box, pass the whole image to ViT instead of failing
                yolo_class_name = "None detected (used full image)"
                yolo_confidence = 0.0
                leaf_crop = img
            
            # 3. Run ViT for disease classification on the cropped leaf (or whole image)
            input_tensor = self.vit_transforms(leaf_crop).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                output = self.vit_model(input_tensor)
                
                # Apply softmax to get probabilities
                probabilities = torch.nn.functional.softmax(output[0], dim=0)
                
                # Get the highest probability class
                top_prob, top_class = torch.max(probabilities, dim=0)
                
                vit_class_idx = int(top_class.item())
                vit_confidence = float(top_prob.item())
                
                # Retrieve the actual class name from the list
                if 0 <= vit_class_idx < len(self.vit_class_names):
                    raw_class_name = self.vit_class_names[vit_class_idx]
                    # Clean up the name (e.g. "Apple___Apple_scab_leaf" -> "Apple - Apple scab leaf")
                    vit_class_name = raw_class_name.replace("___", " - ").replace("__", " - ").replace("_", " ")
                else:
                    vit_class_name = f"Unknown Disease (Class {vit_class_idx})"

            return {
                "status": "success",
                "message": "Diagnosis complete.",
                "diagnosis": {
                    "condition": vit_class_name,
                    "confidence": f"{vit_confidence * 100:.2f}%",
                    "yolo_detection": yolo_class_name,
                    "leaf_detection_confidence": f"{yolo_confidence * 100:.2f}%"
                }
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"An error occurred during diagnosis: {str(e)}"
            }

# Global instance
ml_service = PlantDiagnosticsService()
