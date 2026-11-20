"""Inspect the selected VRM's bind rig at a pose exported by --rig-pose."""

import argparse
import csv
from math import atan2, cos, degrees, pi, sin
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory

import bpy
from mathutils import Matrix, Quaternion, Vector


GLTF_TO_BLENDER = Matrix.Rotation(pi / 2, 4, 'X')


def read_pose(path):
    with path.open(newline='') as stream:
        rows = csv.reader(stream, delimiter='\t')
        label, x, y, z, yaw, scale = next(rows)
        assert label == 'root'
        root = (Matrix.Translation((float(x), float(y), float(z))) @
                Matrix.Rotation(float(yaw), 4, 'Y') @ Matrix.Scale(float(scale), 4))
        bones = {}
        for label, name, *raw in rows:
            assert label == 'bone' and len(raw) == 19 and name not in bones
            values = list(map(float, raw))
            x, y, z, qx, qy, qz, qw = values[:7]
            rest = Matrix.Translation((x, y, z)) @ Quaternion((qw, qx, qy, qz)).to_matrix().to_4x4()
            matrix_rows = [values[start:start + 4] for start in (7, 11, 15)]
            posed = Matrix((*matrix_rows, (0, 0, 0, 1)))
            bones[name] = rest, posed
    return root, bones


def inspect_joint_motion(bones):
    for side in ('L', 'R'):
        def joint(role):
            return bones[f'J_Bip_{side}_{role}']

        chest_rest, chest_pose = bones['J_Bip_C_UpperChest']
        shoulder_rest, shoulder_pose = joint('Shoulder')
        chest = chest_pose @ chest_rest.inverted()
        shoulder = shoulder_pose @ shoulder_rest.inverted()
        collar_motion = degrees(chest.to_quaternion().rotation_difference(shoulder.to_quaternion()).angle)
        elbow_rest, elbow_pose = joint('LowerArm')
        hand_rest, hand_pose = joint('Hand')
        thumb_rest, _ = joint('Thumb1')
        finger_rest, _ = joint('Middle1')
        palm = (thumb_rest.translation - hand_rest.translation).cross(
            finger_rest.translation - hand_rest.translation).normalized()
        axis = (hand_pose.translation - elbow_pose.translation).normalized()

        def across(turn):
            rotated = turn.to_3x3() @ palm
            return (rotated - axis * rotated.dot(axis)).normalized()

        forearm = across(elbow_pose @ elbow_rest.inverted())
        hand = across(hand_pose @ hand_rest.inverted())
        roll = degrees(atan2(axis.dot(forearm.cross(hand)), forearm.dot(hand)))
        print(f'{side} clavicle/chest change {min(collar_motion, 360 - collar_motion):.1f}°, wrist axial change {roll:.1f}°')


def apply_pose(armature, bones):
    rest = {bone.name: bone.bone.matrix_local.copy() for bone in armature.pose.bones}
    armature_world = armature.matrix_world.copy()
    to_armature = armature_world.inverted() @ GLTF_TO_BLENDER
    from_armature = to_armature.inverted()
    for bone in sorted(armature.pose.bones, key=lambda current: len(current.parent_recursive)):
        if bone.name in bones:
            bind, posed = bones[bone.name]
            bone.matrix = to_armature @ posed @ bind.inverted() @ from_armature @ rest[bone.name]
            bpy.context.view_layer.update()


def render_angles(out, root, angles):
    scene = bpy.context.scene
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    scene.camera = camera
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 2.05
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.resolution_x = 544
    scene.render.resolution_y = 544
    scene.render.image_settings.file_format = 'PNG'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'MATERIAL'
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = 'WORLD'
    target = (GLTF_TO_BLENDER @ root).translation + Vector((0.0, 0.0, 0.72))
    for angle in angles:
        yaw = angle * pi / 180
        camera.location = target + 4 * Vector((sin(yaw), -cos(yaw), 0.30))
        camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = str(out / f'angle-{angle:+d}.png')
        bpy.ops.render.render(write_still=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model', type=Path)
    parser.add_argument('pose', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--angles', type=int, nargs='+', default=[0, 60, -60])
    parser.add_argument('--save-blend', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    args.output.mkdir(parents=True, exist_ok=True)
    out = args.output.resolve()
    # VRM 0.x is a GLB container. Blender's standard glTF importer opens
    # the original bytes with the GLB extension and ignores VRM metadata.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with TemporaryDirectory(dir=out, prefix='.vrm-') as working:
        glb = Path(working) / 'source.glb'
        shutil.copyfile(args.model, glb)
        bpy.ops.import_scene.gltf(filepath=str(glb))
    objects = list(bpy.context.scene.objects)
    armature, = [obj for obj in objects if obj.type == 'ARMATURE']
    meshes = [obj for obj in objects if obj.type == 'MESH']
    man = all('PracticeSkirt' not in obj.data.name for obj in meshes)
    print(f'{args.model.name}: {len(armature.data.bones)} bind bones, '
          f'{len(meshes)} meshes, {sum(len(obj.data.vertices) for obj in meshes)} vertices')
    for obj in meshes:
        for modifier in obj.modifiers:
            if modifier.type == 'ARMATURE':
                affine = 'PracticeClothSlippers' in obj.data.name or (man and 'Practice' in obj.data.name)
                modifier.use_deform_preserve_volume = not affine
    root, bones = read_pose(args.pose)
    inspect_joint_motion(bones)
    apply_pose(armature, bones)
    change = GLTF_TO_BLENDER @ root @ GLTF_TO_BLENDER.inverted()
    for obj in objects:
        if obj.parent is None:
            obj.matrix_world = change @ obj.matrix_world
    render_angles(out, root, args.angles)
    if args.save_blend:
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(filepath=str(out / 'pose.blend'))


if __name__ == '__main__':
    main()
