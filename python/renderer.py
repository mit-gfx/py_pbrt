from pathlib import Path
import shutil
import os
import numpy as np

from common import ndarray, create_folder
from project_path import root_path

# This class assumes the following right-handed coordinates:
# - x: left to right;
# - y: near to far;
# - z: bottom to top.
class PbrtRenderer(object):
    def __init__(self, options=None):
        self.__temporary_folder = Path('.tmp')
        create_folder(self.__temporary_folder)
        if options is None: options = {}

        # Image metadata.
        file_name = options['file_name'] if 'file_name' in options else 'output.exr'
        file_name = str(file_name)
        assert file_name.endswith('.png') or file_name.endswith('.exr')
        file_name_only = file_name[:-4]
        self.__file_name_only = file_name_only

        resolution = options['resolution'] if 'resolution' in options else (800, 800)
        resolution = tuple(resolution)
        assert len(resolution) == 2
        resolution = [int(r) for r in resolution]
        self.__resolution = tuple(resolution)

        sample = options['sample'] if 'sample' in options else 4
        sample = int(sample)
        assert sample > 0
        self.__sample = sample

        max_depth = options['max_depth'] if 'max_depth' in options else 4
        max_depth = int(max_depth)
        assert max_depth > 0
        self.__max_depth = max_depth

        # Camera metadata.
        camera_pos = options['camera_pos'] if 'camera_pos' in options else (2, -2.2, 2)
        camera_pos = ndarray(camera_pos).ravel()
        assert camera_pos.size == 3
        self.__camera_pos = camera_pos

        camera_lookat = options['camera_lookat'] if 'camera_lookat' in options else (0.5, 0.5, 0.5)
        camera_lookat = ndarray(camera_lookat).ravel()
        assert camera_lookat.size == 3
        self.__camera_lookat = camera_lookat

        camera_up = options['camera_up'] if 'camera_up' in options else (0, 0, 1)
        camera_up = ndarray(camera_up).ravel()
        assert camera_up.size == 3
        self.__camera_up = camera_up

        fov = options['fov'] if 'fov' in options else 33
        fov = float(fov)
        assert 0 < fov < 180
        self.__fov = fov

        # Lighting.
        lightmap = options['light_map'] if 'light_map' in options else 'lightmap.exr'
        lightmap = Path(root_path) / 'asset/texture/{}'.format(lightmap)
        self.__lightmap = lightmap

        # A list of objects.
        self.__hex_objects = []
        self.__tri_objects = []
        self.__shape_objects = []

    # Input:
    # - tri_mesh: an obj file name.
    # - transforms is a list of rotation, translation, and scaling applied to the mesh applied in the order of
    #   their occurances in transforms.
    #       transforms = [rotation, translation, scaling, ...]
    #       rotation = ('r', (radians, unit_axis.x, unit_axis.y, unit_axis.z))
    #       translation = ('t', (tx, ty, tz))
    #       scaling = ('s', s)
    #   For developers only: Note that we use right-handed coordinate systems in the project but pbrt uses a
    #   left-handed system. As a result, we will take care of transforming the coordinate system in this function.
    # - color: a 3D vector between 0 and 1 or a string of 6 letters in hex.
    # - texture_img: either a texture image name (assumed to be in asset/texture) or 'chkbd_[]_{}' where an integer in []
    #   indicates the number of grids in the checkerboard and a floating point number between 0 and 1 in {} specifies the
    #   darker color in the checkerboard.
    # - material: for advanced users, you can use this dictionary to specify materials as described in the pbrt-v3 user
    #   guide: https://www.pbrt.org/fileformat-v3.html. If material is not None, it will supercede the 'color' argument.
    def add_tri_mesh(self, tri_mesh, transforms=None, color=(.5, .5, .5), texture_img=None, material=None):
        tri_num = len(self.__tri_objects)
        tri_pbrt_short_name = 'tri_{:08d}.pbrt'.format(tri_num)
        tri_pbrt_name = self.__temporary_folder / tri_pbrt_short_name

        tri_obj_name = tri_mesh
        tmp_error_name = self.__temporary_folder / '.tmp.error'
        os.system('{} {} {} 2>{}'.format(str(Path(root_path) / 'external/pbrt_build/obj2pbrt'),
            tri_obj_name, tri_pbrt_name, tmp_error_name))

        lines = ['AttributeBegin\n',]
        # Material.
        if isinstance(color, str):
            assert len(color) == 6
            r = int(color[:2], 16) / 255.0
            g = int(color[2:4], 16) / 255.0
            b = int(color[4:], 16) / 255.0
            color = (r, g, b)
        color = ndarray(color).ravel()
        assert color.size == 3
        for c in color:
            assert 0 <= c <= 1
        r, g, b = color

        if texture_img is None:
            if material is not None:
                # For advanced users only --- it will supercede the color argument.
                assert isinstance(material, dict)
                name = material['name']
                material_line = 'Material "' + name + '"'
                for k, v in material.items():
                    if k == 'name': continue
                    if isinstance(v, float):
                        material_line += ' "float {}" [{:f}]\n'.format(str(k), v)
                    elif isinstance(v, bool):
                        material_line += ' "bool {}" [{}]\n'.format(str(k), 'true' if v else 'false')
                    else:
                        # Assume it is a color type.
                        color_v = ndarray(v)
                        assert color_v.size == 3
                        material_line += ' "color {}" [{:f} {:f} {:f}]\n'.format(str(k),
                            color_v[0], color_v[1], color_v[2])
                lines.append(material_line)
            else:
                lines.append('Material "plastic" "color Kd" [{} {} {}] "color Ks" [{} {} {}] "float roughness" .3\n'.format(
                    r, g, b, r, g, b))
        elif 'chkbd' in texture_img:
            _, square_num, square_color = texture_img.split('_')
            square_num = int(square_num)
            square_color = np.clip(float(square_color), 0, 1)
            lines.append('Texture "checks" "spectrum" "checkerboard"\n')
            lines.append('  "float uscale" [{:d}] "float vscale" [{:d}]\n'.format(square_num, square_num))
            lines.append('  "rgb tex1" [{:f} {:f} {:f}] "rgb tex2" [{:f} {:f} {:f}]\n'.format(
                r, g, b,
                square_color * r, square_color * g, square_color * b
                ))
            lines.append('Material "matte" "texture Kd" "checks"\n')
        else:
            texture_img = Path(root_path) / 'asset/texture/{}'.format(texture_img)
            lines.append('Texture "grid" "color" "imagemap" "string filename" ["{}"]\n'.format(str(texture_img)))
            lines.append('Texture "sgrid" "color" "scale" "texture tex1" "grid" "color tex2" [{} {} {}]\n'.format(r, g, b))
            lines.append('Material "matte" "texture Kd" "sgrid"\n')

        # Transforms.
        # Flipped y because pbrt uses a left-handed system.
        lines.append('Scale 1 -1 1\n')
        if transforms is not None:
            for key, vals in reversed(transforms):
                if key == 's':
                    lines.append('Scale {:f} {:f} {:f}\n'.format(vals, vals, vals))
                elif key == 'r':
                    deg = np.rad2deg(vals[0])
                    ax = vals[1:4]
                    ax /= np.linalg.norm(ax)
                    lines.append('Rotate {:f} {:f} {:f} {:f}\n'.format(deg, ax[0], ax[1], ax[2]))
                elif key == 't':
                    lines.append('Translate {:f} {:f} {:f}\n'.format(vals[0], vals[1], vals[2]))

        # Original shape.
        with open(tri_pbrt_name, 'r') as f:
            lines += f.readlines()

        lines.append('AttributeEnd\n')

        # Write back script.
        with open(tri_pbrt_name, 'w') as f:
            for l in lines:
                f.write(l)

        self.__tri_objects.append(tri_pbrt_short_name)

    # - shape_info: a dictionary.
    def add_shape_mesh(self, shape_info, transforms=None, color=(.5, .5, .5)):
        shape_num = len(self.__shape_objects)
        shape_pbrt_short_name = 'shape_{:08d}.pbrt'.format(shape_num)
        shape_pbrt_name = self.__temporary_folder / shape_pbrt_short_name

        lines = ['AttributeBegin\n',]
        # Material.
        if isinstance(color, str):
            assert len(color) == 6
            r = int(color[:2], 16) / 255.0
            g = int(color[2:4], 16) / 255.0
            b = int(color[4:], 16) / 255.0
            color = (r, g, b)
        color = ndarray(color).ravel()
        assert color.size == 3
        for c in color:
            assert 0 <= c <= 1
        r, g, b = color
        lines.append('Material "plastic" "color Kd" [{} {} {}] "color Ks" [{} {} {}] "float roughness" .3\n'.format(
            r, g, b, r, g, b))
 
        # Transforms.
        # Flipped y because pbrt uses a left-handed system.
        lines.append('Scale 1 -1 1\n')
        if transforms is not None:
            for key, vals in reversed(transforms):
                if key == 's':
                    lines.append('Scale {:f} {:f} {:f}\n'.format(vals, vals, vals))
                elif key == 'r':
                    deg = np.rad2deg(vals[0])
                    ax = vals[1:4]
                    ax /= np.linalg.norm(ax)
                    lines.append('Rotate {:f} {:f} {:f} {:f}\n'.format(deg, ax[0], ax[1], ax[2]))
                elif key == 't':
                    lines.append('Translate {:f} {:f} {:f}\n'.format(vals[0], vals[1], vals[2]))

        # Original shape.
        shape_name = shape_info['name']
        if shape_name == 'curve':
            # This is the only viable option for now.
            points = ndarray(shape_info['point']).ravel()
            assert points.size == 12
            type_info = '"string type" "flat"'
            if 'type' in shape_info:
                type_info = '"string type" "{}"'.format(shape_info['type'])
            width_info = '"float width" [1.0]'
            if 'width' in shape_info:
                width_info = '"float width" [{}]'.format(float(shape_info['width']))
            lines.append('Shape "curve" "point P" [' + ' '.join([str(v) for v in points])
                + '] {} {}\n'.format(type_info, width_info))
        elif shape_name == 'sphere':
            radius = float(shape_info['radius'])
            center = ndarray(shape_info['center']).ravel()
            assert center.size == 3
            lines.append('Translate {:f} {:f} {:f}\n'.format(center[0], center[1], center[2]))
            lines.append('Shape "sphere" "float radius" [{:f}]'.format(radius))
        else:
            raise NotImplementedError

        lines.append('AttributeEnd\n')

        # Write back script.
        with open(shape_pbrt_name, 'w') as f:
            for l in lines:
                f.write(l)

        self.__shape_objects.append(shape_pbrt_short_name)

    # Call this function after you have set up add_hex_mesh and add_tri_mesh.
    def render(self, verbose=False, nproc=None):
        scene_pbrt_name = self.__temporary_folder / 'scene.pbrt'
        with open(scene_pbrt_name, 'w') as f:
            x_res, y_res = self.__resolution
            f.write('Film "image" "integer xresolution" [{:d}] "integer yresolution" [{:d}]\n'.format(x_res, y_res))
            f.write('    "string filename" "{:s}.exr"\n'.format(self.__file_name_only))

            f.write('\n')
            f.write('Sampler "halton" "integer pixelsamples" [{:d}]\n'.format(self.__sample))
            f.write('Integrator "path" "integer maxdepth" {:d}\n'.format(self.__max_depth))

            f.write('\n')
            # Flipped y because pbrt uses a left-handed coordinate system.
            cpx, cpy, cpz = self.__camera_pos
            clx, cly, clz = self.__camera_lookat
            cux, cuy, cuz = self.__camera_up
            f.write('LookAt {:f} {:f} {:f} {:f} {:f} {:f} {:f} {:f} {:f}\n'.format(
                cpx, -cpy, cpz,
                clx, -cly, clz,
                cux, -cuy, cuz))
            f.write('Camera "perspective" "float fov" [{:f}]\n'.format(self.__fov))

            f.write('\n')
            f.write('WorldBegin\n')

            f.write('\n')
            f.write('AttributeBegin\n')
            f.write('LightSource "infinite" "string mapname" "{}" "color scale" [1, 1, 1]\n'.format(str(self.__lightmap)))
            f.write('AttributeEnd\n')

            f.write('\n')
            for hex_pbrt_name in self.__hex_objects:
                f.write('Include "{}"\n'.format(hex_pbrt_name))

            for tri_pbrt_name in self.__tri_objects:
                f.write('Include "{}"\n'.format(tri_pbrt_name))

            for shape_pbrt_name in self.__shape_objects:
                f.write('Include "{}"\n'.format(shape_pbrt_name))

            f.write('\n')
            f.write('WorldEnd\n')

        verbose_flag = ' ' if verbose else '--quiet'
        thread_flag = ' ' if nproc is None else '--nthreads {:d}'.format(int(nproc))
        os.system('{} {} {} {}'.format(str(Path(root_path) / 'external/pbrt_build/pbrt'),
            verbose_flag, thread_flag, scene_pbrt_name))
        os.system('convert {}.exr {}.png'.format(self.__file_name_only, self.__file_name_only))

        os.remove('{}.exr'.format(self.__file_name_only))

        # Cleanup data.
        shutil.rmtree(self.__temporary_folder)