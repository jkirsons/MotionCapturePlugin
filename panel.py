import bpy

class OBJECT_PT_IMUPanel(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "IMU Suit"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_idname = "VIEW3D_PT_imu"
    bl_category = 'Motion Capture'
    
    def draw(self, context):
        settings = context.scene.mc_settings
        
        label = "Stop Capture" if settings.start else "Start Capture"
        
        row = self.layout.row()
        row.operator('wm.mocap_install_packages_operator')
        row = self.layout.row()
        row.prop(settings, 'start', text=label, toggle=True, icon="RESTRICT_VIEW_OFF")   
        row = self.layout.row()    
        row.prop(settings, "fps")
        row.prop(settings, 'port')
        
        self.layout.separator()
        box = self.layout.box()
        box.label(text="Pose Config:")
        box.prop(settings, "obj")

        row = box.row()
        row.operator('wm.mocap_set_tpose_operator')
        
        self.layout.separator()
        box = self.layout.box()
        row = box.row()
        row.label(text="Selected Bone: " + bpy.context.active_pose_bone.name if bpy.context.active_pose_bone is not None else "" )
        row.enabled = True if bpy.context.active_pose_bone is not None else False
        row = box.row()
        row.enabled = True if bpy.context.active_pose_bone is not None else False
        bone = row.operator('wm.mocap_set_bone_operator')
        if context.scene.mc_settings.selected_id != '':
            bone.sensor_str, bone.sensor_x, bone.sensor_y = context.scene.mc_settings.keyToSensors(context.scene.mc_settings.selected_id)

        self.layout.separator()
        box = self.layout.box()
        box.label(text="IMU Node Config:")

        if context.scene.mc_settings.selected_id != '':
            row = box.row()
            sensor = settings.mapping[settings.selected_id[2:]]['imu'][int(context.scene.mc_settings.selected_id[0:1])][int(context.scene.mc_settings.selected_id[1:2])]
            if 'bone_name' in sensor:
                row.label(text="Mapped Bone: " + sensor['bone_name'])      
        
        row = box.row()
        row.prop(settings, "selected_id")
        
        box = self.layout
        box.prop(settings, "ui_vector")
        box.prop(settings, "ui_track")
        box.prop(settings, "ui_up")
        
        self.layout.prop(settings, "template")


register, unregister = bpy.utils.register_classes_factory([OBJECT_PT_IMUPanel])

if __name__ == "__main__":
    register()