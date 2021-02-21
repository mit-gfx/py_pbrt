from pathlib import Path
import os
import numpy as np

from renderer import PbrtRenderer
from common import create_folder
from project_path import root_path

if __name__ == '__main__':
    # Create a folder to store the information.
    output_folder = Path('bunny')
    create_folder(output_folder)

    # The asset folder.
    asset_folder = Path(root_path) / 'asset'

    # Create the render.
    options = {
        'file_name': str(output_folder / 'demo.png'),
        'light_map': 'uffizi-large.exr',
        'sample': 4,
        'max_depth': 4,
        'camera_pos': (0, -2, 0.8),
        'camera_lookat': (0, 0, 0),
        'camera_up': (0, 0, 1),
    }
    renderer = PbrtRenderer(options)

    # Add the bunny to the scene.
    renderer.add_tri_mesh(asset_folder / 'mesh/bunny.obj',
        transforms=[
            ('s', 1 / 400),
        ],
        color=(.3, .7, .5))

    # Add the background.
    renderer.add_tri_mesh(asset_folder / 'mesh/curved_ground.obj',
        texture_img='chkbd_24_0.7')

    # Render.
    renderer.render(verbose=True)

    # Display.
    os.system('eog {}'.format(output_folder / 'demo.png'))