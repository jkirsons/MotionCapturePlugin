import bpy, mathutils, math, json, functools, time

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
    timer: bpy.props.IntProperty(name="Timer", default=0)
    time = 0

    def setInit(self, bone):
        bone.rotation_mode = 'QUATERNION'
        bone.rotation_quaternion = mathutils.Quaternion()

    def updateBones(self, bone, func):
        if func(bone):
            bpy.context.view_layer.update()
        for b in bone.children:
            self.updateBones(b, func)

    def setTPose(self, context):
        for bone in context.scene.mc_settings.obj.pose.bones:
            # Find parent bone and iterate through children
            if bone.parent == None:
                self.updateBones(bone, self.setInit)
        bpy.context.view_layer.update()
        context.scene.mc_settings.iterateSensors(context.scene.mc_settings.initPoseFunc)

    def modal(self, context, event):
        if event.type == 'TIMER':  
            if int(time.time() - self.start) > self.time:
                self.time += 1
                if self.time >= self.timer:
                    self.setTPose(context)
                    self.report({'INFO'},"T-Pose Set!")
                    if hasattr(self, '_timer'):
                        wm = context.window_manager
                        wm.event_timer_remove(self._timer)
                    return {'CANCELLED'}
                self.report({'INFO'},"%d" % (self.timer - self.time))
        return {'PASS_THROUGH'}

    def execute(self, context):
        if self.timer > 0:
            self.time = 0
            self.start = time.time()
            wm = context.window_manager
            self._timer = wm.event_timer_add(1, window=context.window)
            wm.modal_handler_add(self)
            self.report({'INFO'},"%d" % self.timer)
            return {'RUNNING_MODAL'}

        self.setTPose(context)
        return {'FINISHED'}       

register, unregister = bpy.utils.register_classes_factory([SetBoneOperator, SetTPoseOperator])

if __name__ == "__main__":
    register()        