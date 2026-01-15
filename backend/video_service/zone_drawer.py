import cv2
import json


class ZoneDrawer:
    def __init__(self):
        self.points = []
        self.done = False

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.points.append([x, y])
            print(f"Point added: {x}, {y}")

    def draw(self, frame):
        # draw points
        for p in self.points:
            cv2.circle(frame, tuple(p), 5, (0, 0, 255), -1)

        # draw lines
        if len(self.points) > 1:
            for i in range(len(self.points) - 1):
                cv2.line(
                    frame,
                    tuple(self.points[i]),
                    tuple(self.points[i + 1]),
                    (0, 0, 255),
                    2,
                )

    def close_polygon(self, frame):
        if len(self.points) > 2:
            cv2.line(
                frame,
                tuple(self.points[-1]),
                tuple(self.points[0]),
                (0, 0, 255),
                2,
            )

    def save(self, filename="zones.json"):
        zone = {
            "id": 1,
            "name": "User Zone",
            "polygon": self.points,
            "forbidden_classes": ["person"],
        }

        with open(filename, "w") as f:
            json.dump([zone], f, indent=4)

        print(f"Zone saved to {filename}")
