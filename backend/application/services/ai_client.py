import requests

AI_URL = "http://ai:9000"


def enqueue_frame(camera_id, frame):

    try:
        requests.post(
            f"{AI_URL}/enqueue",
            json={
                "camera_id": camera_id,
                "frame": frame
            },
            timeout=0.2
        )
    except:
        pass


def get_result():

    try:
        r = requests.get(f"{AI_URL}/result", timeout=0.2)

        if r.status_code == 200:
            return r.json()

    except:
        pass

    return None
