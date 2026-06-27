import json
from pathlib import Path
import pandas as pd
from joblib import load
from backend.app.extraction.pdf_feature_extractor import extract_pdf_features


MODEL_PATH = Path("models/ocr_decision_model.joblib")
METADATA_PATH = Path("models/ocr_model_metadata.json")


def load_model_metadata() -> dict:
    if not METADATA_PATH.exists():
        raise FileNotFoundError(f"OCR model metadata not found: {METADATA_PATH}")

    with open(METADATA_PATH, "r", encoding="utf-8") as metadata_file:
        return json.load(metadata_file)


def load_ocr_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"OCR decision model not found: {MODEL_PATH}")

    return load(MODEL_PATH)


def predict_ocr_requirement(file_path: str) -> dict:
    model = load_ocr_model()
    metadata = load_model_metadata()

    feature_columns = metadata["feature_columns"]
    features = extract_pdf_features(file_path)

    input_data = pd.DataFrame([features])
    input_data = input_data.reindex(columns=feature_columns, fill_value=0)

    prediction = model.predict(input_data)[0]

    confidence = None
    probabilities = None

    if hasattr(model, "predict_proba"):
        probability_values = model.predict_proba(input_data)[0]
        class_labels = list(model.classes_)

        probabilities = {
            str(class_label): float(probability)
            for class_label, probability in zip(class_labels, probability_values)
        }

        confidence = probabilities[str(prediction)]

    return {
        "ocr_required": str(prediction),
        "confidence": confidence,
        "probabilities": probabilities,
        "model_name": metadata.get("model_name"),
        "model_version": metadata.get("version"),
        "file_path": file_path,
        "features": features,
    }

