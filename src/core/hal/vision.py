import io
import time
import threading
from typing import Optional, Protocol, Tuple, Union
import numpy as np

# Try importing mss for software capture
try:
    import mss
    import mss.tools
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

# Try importing cv2 for hardware/camera capture
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

class VisionProvider(Protocol):
    """Protocol for vision providers (Source of visual data)."""
    def capture(self, force: bool = False) -> Optional[bytes]:
        """Capture a frame and return it as JPEG bytes."""
        ...
    
    def cleanup(self):
        """Release resources."""
        ...

class SoftwareCapture:
    """Captures the primary screen using MSS (Platform Independent Software Capture)."""
    def __init__(self, monitor_index: int = 1):
        if not HAS_MSS:
            raise ImportError("mss is required for SoftwareCapture. pip install mss")
        self.monitor_index = monitor_index
        self._thread_local = threading.local()
        self.last_frame_array: Optional[np.ndarray] = None

    @property
    def sct(self):
        """Get or create mss instance for the current thread."""
        if not hasattr(self._thread_local, 'sct'):
            self._thread_local.sct = mss.mss()
        return self._thread_local.sct

    @property
    def monitor(self):
        """Get the monitor for the current thread's mss instance."""
        try:
            return self.sct.monitors[self.monitor_index]
        except IndexError:
            return self.sct.monitors[1]

    def capture(self, force: bool = False) -> Optional[bytes]:
        """Captures screen, converts to numpy for fast downsampled diffing, resizes to max 1024, and compresses to JPEG."""
        try:
            # 1. Capture to raw pixels (using thread-local mss)
            sct_img = self.sct.grab(self.monitor)
            
            # Use PIL if OpenCV is not available
            if not HAS_CV2:
                from PIL import Image as PILImage
                img = PILImage.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                
                # Check change via low-res thumbnail if not forced
                if not force and self.last_frame_array is not None:
                    # Simple fast downsampled check in PIL
                    small_curr = img.resize((64, 64), PILImage.NEAREST)
                    small_last = self.last_frame_array.resize((64, 64), PILImage.NEAREST)
                    # Check if significantly changed
                    diff = 0
                    curr_data = list(small_curr.getdata())
                    last_data = list(small_last.getdata())
                    for p1, p2 in zip(curr_data, last_data):
                        diff += abs(p1[0]-p2[0]) + abs(p1[1]-p2[1]) + abs(p1[2]-p2[2])
                    mean_diff = diff / (64 * 64 * 3)
                    if mean_diff <= 255 * 0.05:
                        return None
                
                self.last_frame_array = img
                
                # Resize if larger than 1024 to speed up transmission
                if img.width > 1024 or img.height > 1024:
                    img.thumbnail((1024, 1024))
                byte_io = io.BytesIO()
                img.save(byte_io, format="JPEG", quality=75)
                return byte_io.getvalue()
            
            # OpenCV flow:
            img_array = np.array(sct_img)
            img_bgr = img_array[:, :, :3]
            
            if not force and not self._has_changed_significantly_fast(img_bgr):
                return None
                
            self.last_frame_array = img_bgr
            
            # Resize using OpenCV (incredibly fast)
            h, w = img_bgr.shape[:2]
            max_dim = 1024
            if w > max_dim or h > max_dim:
                scale = max_dim / max(w, h)
                img_bgr = cv2.resize(img_bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
                
            # Compress to JPEG with 75% quality
            _, buffer = cv2.imencode('.jpg', img_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            return buffer.tobytes()
            
        except Exception as e:
            print(f"Software Capture Error: {e}")
            return None

    def _has_changed_significantly_fast(self, current_frame: np.ndarray, threshold: float = 0.05) -> bool:
        """Fast pixel difference check using a downsampled image."""
        if self.last_frame_array is None:
            return True
        # Resize both to 64x64 for instant difference check
        small_curr = cv2.resize(current_frame, (64, 64), interpolation=cv2.INTER_AREA)
        small_last = cv2.resize(self.last_frame_array, (64, 64), interpolation=cv2.INTER_AREA)
        diff = np.abs(small_curr.astype(int) - small_last.astype(int))
        mean_diff = np.mean(diff)
        return mean_diff > (255 * threshold)

    def cleanup(self):
        if hasattr(self._thread_local, 'sct'):
            self._thread_local.sct.close()


class PeripheralCapture:
    """Captures from a UVC HDMI Capture Card or USB Camera using OpenCV."""
    def __init__(self, device_index: int = 0):
        if not HAS_CV2:
            raise ImportError("opencv-python is required for PeripheralCapture.")
        self.cap = cv2.VideoCapture(device_index)
        
        # Optimize for latency
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        # Try to secure 720p or 1080p depending on performance
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open video device {device_index}")

    def capture(self, force: bool = False) -> Optional[bytes]:
        # Note: force is accepted but peripheral cameras are usually dynamic
        ret, frame = self.cap.read()
        if not ret:
            return None
            
        # Resize to max 1024
        h, w = frame.shape[:2]
        max_dim = 1024
        if w > max_dim or h > max_dim:
            scale = max_dim / max(w, h)
            frame = cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
            
        # JPEG encode in-memory with 75% quality
        _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        return buffer.tobytes()

    def cleanup(self):
        if self.cap.isOpened():
            self.cap.release()


def get_vision_provider(source_type: str = 'DISPLAY', index: int = 0) -> VisionProvider:
    """Factory to get the appropriate vision provider."""
    if source_type == 'DISPLAY':
        return SoftwareCapture(monitor_index=index + 1 if index == 0 else index)
    elif source_type == 'CAMERA':
        return PeripheralCapture(device_index=index)
    else:
        raise ValueError(f"Unknown source_type: {source_type}")
