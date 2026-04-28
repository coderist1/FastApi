from transformers import pipeline

class Model:
    def __init__(self):
        self.classifier = pipeline("sentiment-analysis")

    def predict(self, text: str):
        result = self.classifier(text)[0]
        return {"label": result["label"], "score": float(result["score"])}

model_instance = Model()