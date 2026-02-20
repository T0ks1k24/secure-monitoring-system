from queue import Queue

frame_queues = {}

def get_camera_queue(camera_id):

    if camera_id not in frame_queues:
        frame_queues[camera_id] = Queue(maxsize=10)

    return frame_queues[camera_id]
