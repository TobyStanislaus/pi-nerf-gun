from ultralytics import YOLO
import statistics


def load_model(path):
    model = YOLO(path) 
    return model


def detect_image(model, image):
    results = model(image, verbose=False)[0]
    for result in results.boxes.data.tolist():
        x1, y1, x2, y2, conf, type = result
        if conf>0.5:
            return True

    return False

def print_stats(name, times):
    if times:
        print(f"{name}: avg={statistics.mean(times):.4f}s, "
                f"min={min(times):.4f}s, max={max(times):.4f}s, "
                f"stdev={statistics.stdev(times) if len(times) > 1 else 0:.4f}s "
                f"(samples: {len(times)})")

