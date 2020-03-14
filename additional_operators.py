import bpy, mathutils, math, json

class SetBoneOperator(bpy.types.Operator):
    """Set Bone"""
    bl_idname = "wm.mocap_set_bone_operator"
    bl_label = "Map Bone to IMU Node"
    sensor: bpy.props.IntProperty(name="Sensor")
    sensor_str: bpy.props.StringProperty(name="SensorStr")
    sensor_x: bpy.props.IntProperty(name="SensorX")
    sensor_y: bpy.props.IntProperty(name="SensorY")
    
    def execute(self, context):
        #context.scene.mc_settings.bones.append(bpy.context.active_pose_bone)
        context.scene.mc_settings.mapping[self.sensor_str]['imu'][self.sensor_x][self.sensor_y]['bone_name'] = '%s' % context.active_pose_bone.name
        context.scene.mc_settings.save(context.scene.mc_settings.mapping)
        return {'FINISHED'}

class SetTPoseOperator(bpy.types.Operator):
    """Set T-Pose"""
    bl_idname = "wm.mocap_set_tpose_operator"
    bl_label = "Set T-Pose"
    clear: bpy.props.BoolProperty(name="Clear", default=False)
    
    def initBonePos(self, bone):
        if bone.name in self.settings.bone_names:
            # Keep reference to this bone
            self.settings.bones.append(bone)
            index = self.settings.bone_names.index(bone.name)        
            if self.clear:
                self.settings.offset[index] = mathutils.Quaternion()
            else:
                bone.rotation_mode = 'QUATERNION'
                bone.rotation_quaternion = mathutils.Quaternion()
                bpy.context.view_layer.update()
                self.settings.matrix[index] = bone.matrix.to_quaternion()
                self.settings.offset[index] = self.settings.position[index]
            return True
        return False

    def setInit(self, bone):
        bone.rotation_mode = 'QUATERNION'
        bone.rotation_quaternion = mathutils.Quaternion()

    def updateBones(self, bone, func):
        if func(bone):
            bpy.context.view_layer.update()
        for b in bone.children:
            self.updateBones(b, func)
            
    def execute(self, context):
        for bone in context.scene.mc_settings.obj.pose.bones:
            # Find parent bone and iterate through children
            if bone.parent == None:
                self.updateBones(bone, self.setInit)
        bpy.context.view_layer.update()
        context.scene.mc_settings.iterateSensors(context.scene.mc_settings.initPoseFunc)


        return {'FINISHED'}       

register, unregister = bpy.utils.register_classes_factory([SetBoneOperator, SetTPoseOperator])

if __name__ == "__main__":
    register()        