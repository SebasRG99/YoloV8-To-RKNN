import cv2
import numpy as np
import platform
from rknnlite.api import RKNNLite
from imutils.video import FPS
import time
from lib.postprocess_cp38 import yolov8_post_process, letterbox_reverse_box
import lib.config as config
import argparse

# Construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-i", "--inputtype", required=False, default="cam2",
                help="Select input cam, cam2, file")
ap.add_argument("-f", "--filename", required=False, default="skyfall.mp4",
                help="file video (.mp4)")
args = vars(ap.parse_args())

IMG_SIZE = config.IMG_SIZE
CLASSES = config.CLASSES
DEVICE_COMPATIBLE_NODE = config.DEVICE_COMPATIBLE_NODE
RK356X_RKNN_MODEL = config.RK356X_RKNN_MODEL
RK3588_RKNN_MODEL = config.RK3588_RKNN_MODEL

def get_host():
    system = platform.system()
    machine = platform.machine()
    os_machine = system + '-' + machine
    if os_machine == 'Linux-aarch64':
        try:
            with open(DEVICE_COMPATIBLE_NODE) as f:
                device_compatible_str = f.read()
                if 'rk3588' in device_compatible_str:
                    host = 'RK3588'
                else:
                    host = 'RK356x'
        except IOError:
            print(f'Read device node {DEVICE_COMPATIBLE_NODE} failed.')
            exit(-1)
    else:
        host = os_machine
    return host

def draw(image, boxes, scores, classes, dw, dh):
    """Draw the boxes on the image.

    # Argument:
        image: original image.
        boxes: ndarray, boxes of objects.
        classes: ndarray, classes of objects.
        scores: ndarray, scores of objects.
        all_classes: all classes name.
    """
    for box, score, cl in zip(boxes, scores, classes):
        top, left, right, bottom = box
#        print('class: {}, score: {}'.format(CLASSES[cl], score))
#        print('box coordinate left,top,right,down: [{}, {}, {}, {}]'.format(top, left, right, bottom))

        ##Transform Box to original image
        top, left, right, bottom = letterbox_reverse_box(top, left, right, bottom, config.CAM_WIDTH, config.CAM_HEIGHT, config.IMG_SIZE, config.IMG_SIZE, dw, dh)

        top = int(top)
        left = int(left)
        right = int(right)
        bottom = int(bottom)

        cv2.rectangle(image, (top, left), (right, bottom), (255, 0, 0), 2)
        cv2.putText(image, '{0} {1:.2f}'.format(CLASSES[cl], score),
                    (top, left - 6),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0, 0, 255), 2)

def letterbox(im, new_shape=(640, 640), color=(0, 0, 0)):
    # Resize and pad image while meeting stride-multiple constraints
    shape = im.shape[:2]  # current shape [height, width]
    if isinstance(new_shape, int):
        new_shape = (new_shape, new_shape)

    # Scale ratio (new / old)
    r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])

    # Compute padding
    ratio = r, r  # width, height ratios
    new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
    dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - new_unpad[1]  # wh padding

    dw /= 2  # divide padding into 2 sides
    dh /= 2

    if shape[::-1] != new_unpad:  # resize
        im = cv2.resize(im, new_unpad, interpolation=cv2.INTER_LINEAR)
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    im = cv2.copyMakeBorder(im, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)  # add border
    return im, ratio, (dw, dh)

def open_cam_usb(dev, width, height):
    gst_str = ("v4l2src device={} ! "
               "image/jpeg, width={}, height={}, framerate=30/1 ! "
               "jpegdec ! videoconvert ! appsink").format(dev, width, height)
    print("Using GStreamer pipeline:", gst_str)  # Debugging print
    vs = cv2.VideoCapture(gst_str, cv2.CAP_GSTREAMER)
    print("VideoCapture opened:", vs.isOpened())  # Debugging print
    return vs

if __name__ == '__main__':
    host_name = get_host()
    if host_name == 'RK356x':
        rknn_model = RK356X_RKNN_MODEL
    elif host_name == 'RK3588':
        rknn_model = RK3588_RKNN_MODEL
    else:
        print(f"This demo cannot run on the current platform: {host_name}")
        exit(-1)

    rknn_lite = RKNNLite()

    print('--> Load RKNN model')
    ret = rknn_lite.load_rknn(rknn_model)
    if ret != 0:
        print('Load RKNN model failed')
        exit(ret)
    print('done')

    print('--> Init runtime environment')
    if host_name == 'RK3588':
        ret = rknn_lite.init_runtime(core_mask=RKNNLite.NPU_CORE_0)
    else:
        ret = rknn_lite.init_runtime()
    if ret != 0:
        print('Init runtime environment failed')
        exit(ret)
    print('done')

    # Create Stream from Webcam
    cam_dev = "/dev/video0"  # Asegúrate de que este es el dispositivo correcto
    vs = open_cam_usb(cam_dev, config.CAM_WIDTH, config.CAM_HEIGHT)

    time.sleep(2.0)
    fps = FPS().start()

    if not vs.isOpened():
        print("Cannot capture from camera. Exiting.")
        quit()

    prev_frame_time = 0
    new_frame_time = 0

    # Loop over the frames from the video stream
    while True:
        print("Reading frame...")  # Debugging print
        ret, frame = vs.read()
        if not ret:
            print("Can't receive frame (stream end?). Exiting ...")
            break

        print("Frame received.")  # Debugging print
        new_frame_time = time.time()
        show_fps = 1 / (new_frame_time - prev_frame_time)
        prev_frame_time = new_frame_time
        show_fps = int(show_fps)
        show_fps = f"{show_fps} FPS"

        ori_frame = frame
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame, ratio, (dw, dh) = letterbox(frame, new_shape=(IMG_SIZE, IMG_SIZE))

        # Asegúrate de que la imagen tiene 4 dimensiones
        if frame.ndim == 3:
            frame = np.expand_dims(frame, axis=0)

        # Inference
        outputs = rknn_lite.inference(inputs=[frame])
        print("Inference done.")  # Debugging print

        # Verifica si outputs es None
        if outputs is None:
            print("Inference failed.")
            break

        # Post process
        input0_data = outputs[0]
        input1_data = outputs[1]
        input2_data = outputs[2]

        input0_data = input0_data.reshape([3, -1] + list(input0_data.shape[-2:]))
        input1_data = input1_data.reshape([3, -1] + list(input1_data.shape[-2:]))
        input2_data = input2_data.reshape([3, -1] + list(input2_data.shape[-2:]))

        input_data = list()
        input_data.append(np.transpose(input0_data, (2, 3, 0, 1)))
        input_data.append(np.transpose(input1_data, (2, 3, 0, 1)))
        input_data.append(np.transpose(input2_data, (2, 3, 0, 1)))

        boxes, classes, scores = yolov5_post_process(input_data)

        img_1 = ori_frame
        if boxes is not None:
            draw(img_1, boxes, scores, classes, dw, dh)

        cv2.putText(img_1, show_fps, (7, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 255, 0), 1, cv2.LINE_AA)
        print("Showing frame...")  # Debugging print
        cv2.imshow("yolov5 post process result",img_1)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break

        fps.update()

    rknn_lite.release()
    vs.release()
    cv2.destroyAllWindows()
    fps.stop()
    print(f"[INFO] elapsed time: {fps.elapsed():.2f}")
    print(f"[INFO] approx. FPS: {fps.fps():.2f}")