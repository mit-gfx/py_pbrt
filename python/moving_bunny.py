from pathlib import Path
import os
import numpy as np

from renderer import PbrtRenderer
from common import create_folder, export_mp4, print_info
from project_path import root_path

if __name__ == '__main__':
    # Create a folder to store the information.
    output_folder = Path('moving_bunny')
    create_folder(output_folder)

    # The asset folder.
    asset_folder = Path(root_path) / 'asset'

    frame_num = 20
    for i in range(frame_num):
        # Create the render.
        options = {
            'file_name': str(output_folder / '{:04d}.png'.format(i)),
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
                ('r', (i / frame_num * np.pi / 2, 0, 0, 1,)),
                ('t', (i / frame_num * 0.25, 0, 0))
            ],
            color=(.3, .7, .5))

        # Add the background.
        renderer.add_tri_mesh(asset_folder / 'mesh/curved_ground.obj',
            texture_img='chkbd_24_0.7')

        # Render.
        renderer.render()

        # Print progress.
        print_info('{:d}/{:d} done...'.format(i, frame_num))

    # Export to mp4.
    export_mp4(output_folder, output_folder / 'demo.mp4', fps=frame_num)
    print_info('Please open {} to see the video'.format(output_folder / 'demo.mp4'))