import numpy as np

def ndarray(val):
    return np.asarray(val, dtype=np.float64)

###############################################################################
# Pretty print.
###############################################################################
def print_error(*message):
    print('\033[91m', 'ERROR ', *message, '\033[0m')

def print_ok(*message):
    print('\033[92m', *message, '\033[0m')

def print_warning(*message):
    print('\033[93m', *message, '\033[0m')

def print_info(*message):
    print('\033[96m', *message, '\033[0m')

class PrettyTabular(object):
    def __init__(self, head):
        self.head = head

    def head_string(self):
        line = ''
        for key, value in self.head.items():
            if 's' in value:
                dummy = value.format('0')
            else:
                dummy = value.format(0)
            span = max(len(dummy), len(key)) + 2
            key_format = '{:^' + str(span) + '}'
            line += key_format.format(key)
        return line

    def row_string(self, row_data):
        line = ''
        for key, value in self.head.items():
            data = value.format(row_data[key])
            span = max(len(key), len(data)) + 2
            line += ' ' * (span - len(data) - 1) + data + ' '
        return line

###############################################################################
# Folder.
###############################################################################
import shutil
import os
def create_folder(folder_name, exist_ok=False):
    if not exist_ok and os.path.isdir(folder_name):
        shutil.rmtree(folder_name)
    os.makedirs(folder_name, exist_ok=exist_ok)

def delete_folder(folder_name):
    shutil.rmtree(folder_name)

###############################################################################
# Rotation.
###############################################################################
# Input (rpy): a 3D vector (roll, pitch, yaw).
# Output (R): a 3 x 3 rotation matrix.
def rpy_to_rotation(rpy):
    rpy = ndarray(rpy).ravel()
    assert rpy.size == 3
    roll, pitch, yaw = rpy

    cr, sr = np.cos(roll), np.sin(roll)
    R_roll = ndarray([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    cp, sp = np.cos(pitch), np.sin(pitch)
    R_pitch = ndarray([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    cy, sy = np.cos(yaw), np.sin(yaw)
    R_yaw = ndarray([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])

    return R_yaw @ R_pitch @ R_roll

###############################################################################
# Export videos.
###############################################################################
import imageio
def export_gif(folder_name, gif_name, fps, name_prefix=''):
    frame_names = [os.path.join(folder_name, f) for f in os.listdir(folder_name)
        if os.path.isfile(os.path.join(folder_name, f)) and f.startswith(name_prefix) and f.endswith('.png')]
    frame_names = sorted(frame_names)

    # Read images.
    images = [imageio.imread(f) for f in frame_names]
    if fps > 0:
        imageio.mimsave(gif_name, images, fps=fps)
    else:
        imageio.mimsave(gif_name, images)

from pathlib import Path
def export_mp4(folder_name, mp4_name, fps, name_prefix=''):
    frame_names = [os.path.join(folder_name, f) for f in os.listdir(folder_name)
        if os.path.isfile(os.path.join(folder_name, f)) and f.startswith(name_prefix) and f.endswith('.png')]
    frame_names = sorted(frame_names)

    # Create a temporary folder.
    tmp_folder = Path('_export_mp4')
    create_folder(tmp_folder, exist_ok=False)
    for i, f in enumerate(frame_names):
        shutil.copyfile(f, tmp_folder / '{:08d}.png'.format(i))

    os.system('ffmpeg -r ' + str(fps) + ' -i ' + str(tmp_folder / '%08d.png') + ' -vcodec mpeg4 -y ' + str(mp4_name))

    # Delete temporary folder.
    delete_folder(tmp_folder)