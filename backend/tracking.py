from deep_sort_realtime.deepsort_tracker import DeepSort

tracker = DeepSort(
    max_age=30,
    n_init=2,
    max_cosine_distance=0.3,
)


def update_tracks(detections):
    ds_input = []
    for det in detections:
        x1, y1, x2, y2 = det["bbox"]
        ds_input.append(([x1, y1, x2 - x1, y2 - y1], det["conf"], det["cls"]))

    tracks = tracker.update_tracks(ds_input, frame=None)

    tracked = []
    for t in tracks:
        if not t.is_confirmed():
            continue

        l, t2, r, b = t.to_ltrb()

        tracked.append({
            "track_id": t.track_id,
            "bbox": (float(l), float(t2), float(r), float(b)),
            "cls": int(getattr(t, "det_class", -1)),
            "conf": float(getattr(t, "det_conf", 1.0))
        })

    return tracked


