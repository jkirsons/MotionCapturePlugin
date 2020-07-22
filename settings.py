import bpy, mathutils, math, json

class MotionCaptureSettings(bpy.types.PropertyGroup):
    config_file_name = 'Config_main'

    # Active sensors (ESP32's)
    machine_ids = {}

    # Active sensor data
    sensor_data = {}
        # {'192.168.1.105': 
        #   {'imu': [
        #       [{}, {'position': Quaternion((0.6793757081031799, -0.009521391242742538, 0.02014140412211418, -0.733452320098877))}], 
        #       [{}, {}]
        #   ]}}

    # All sensors - mappings - saved to file
    mapping = {}
        # {"b'L\\x11\\xaet\\xd6p\\x00\\x00\\x01\\xa8'": 
        # {"imu": [[{"forward": [0.0, 0.0, 0.0], "up": [0.0, 0.0, 0.0], "bone_name": ""}, 
        #           {"forward": [0.0, 0.0, 0.0], "up": [0.0, 0.0, 0.0], "bone_name": ""}], 
        #          [{"forward": [0.0, 0.0, 0.0], "up": [0.0, 0.0, 0.0], "bone_name": ""}, 
        #           {"forward": [0.0, 0.0, 0.0], "up": [0.0, 0.0, 0.0], "bone_name": ""}
        #         ]]
        # }}

    track_enum = [
    ("X", "X", "", 1),
    ("-X", "-X", "", 2),
    ("Y", "Y", "", 3),
    ("-Y", "-Y", "", 4),
    ("Z", "Z", "", 5),
    ("-Z", "-Z", "", 6),
    ]

    up_enum = [
    ("X", "X", "", 1),
    ("Y", "Y", "", 3),
    ("Z", "Z", "", 5),
    ("None", "None", "", 6),
    ]

    dir_enum = { "X": mathutils.Vector((1,0,0)), "-X": mathutils.Vector((-1,0,0)), 
                 "Y": mathutils.Vector((0,1,0)), "-Y": mathutils.Vector((0,-1,0)), 
                 "Z": mathutils.Vector((0,0,1)), "-Z": mathutils.Vector((0,0,-1)) }

    class ComplexEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, mathutils.Vector):
                return [obj.x, obj.y, obj.z]
            if isinstance(obj, mathutils.Quaternion):
                return [obj.w, obj.x, obj.y, obj.z]
            if isinstance(obj, bytearray):
                return [str(obj)]
            return json.JSONEncoder.default(self, obj)  

    def idToIp(self, id):
        for ip in self.machine_ids:
            if self.machine_ids[ip] == id:
                return ip
        return 'not connected'

    def update_function(self, context):
        if context.scene.mc_settings.start == True:
            bpy.ops.wm.mocap_set_tpose_operator('EXEC_DEFAULT')
            bpy.ops.wm.mocap_operator('EXEC_DEFAULT')    
            
    def save(self, val):
        if not self.config_file_name in bpy.data.texts:
            bpy.data.texts.new(self.config_file_name)
        bpy.data.texts[self.config_file_name].clear()
        bpy.data.texts[self.config_file_name].write(json.dumps(val, cls=self.ComplexEncoder))

        # update sensors
        self.iterateSensors(self.initPoseFunc)

    def keyToSensors(self, key):
        if key == '': return None, None, None
        sensor_str = key[2:]
        sensor_x = int(key[0:1])
        sensor_y = int(key[1:2])
        return sensor_str, sensor_x, sensor_y
        
    def get_val_U(self):
        m_id, x, y = self.keyToSensors(self.selected_id)
        if not m_id in self.mapping: return 'Y'
        for v in self.up_enum:
            if v[0] == self.mapping[m_id]["imu"][x][y]['mirror']:
                return v[3]
        return 'Y'
        #return self.mapping[m_id]["imu"][x][y]['mirror']

    def set_val_U(self, value):
        m_id, x, y = self.keyToSensors(self.selected_id)
        if not m_id in self.mapping: return
        for v in self.up_enum:
            if v[3] == value:
                self.mapping[m_id]["imu"][x][y]['mirror'] = v[0]
        self.save(self.mapping)

    def get_val_T(self):
        m_id, x, y = self.keyToSensors(self.selected_id)
        if not m_id in self.mapping: return 'Z'
        for v in self.track_enum:
            if v[0] == self.mapping[m_id]["imu"][x][y]['forward']:
                return v[3]
        return 'Z'
        #return self.mapping[m_id]["imu"][x][y]['forward']

    def set_val_T(self, value):
        m_id, x, y = self.keyToSensors(self.selected_id)
        if not m_id in self.mapping: return
        for v in self.track_enum:
            if v[3] == value:
                self.mapping[m_id]["imu"][x][y]['forward'] =  v[0]
        self.save(self.mapping)

    def swapUpdate(self, context):
        # update sensors
        self.iterateSensors(self.initPoseFunc)

    fps: bpy.props.FloatProperty(name="FPS")
    start: bpy.props.BoolProperty(name="Start Capture", update=update_function, default=False)
    port: bpy.props.IntProperty(name="Port", default=61111)
    
    obj: bpy.props.PointerProperty(name="Rig", type=bpy.types.Object)
    
    # Object to repeat for debug visuals
    template: bpy.props.PointerProperty(name="Debug Template", type=bpy.types.Object)
    
    def idCallback(self, context):
        if self.mapping == {}: self.loadMappings()
        ret = []
        for machine_id in self.mapping:
            for x, imu in enumerate(self.mapping[machine_id]['imu']):
                for y, sensor in enumerate(imu):
                    machine_ip = 'not connected'
                    for ip in self.machine_ids:
                        if self.machine_ids[ip] == machine_id:
                            machine_ip = ip
                    ret.append((str(x)+str(y)+machine_id, machine_ip + "[" + str(x) + "] [" + str(y) + "] - " + sensor['bone_name'], machine_ip))
        return ret

    selected_id: bpy.props.EnumProperty(items=idCallback, name="Node")

    # IMU pyhsical orientation
    ui_forward: bpy.props.EnumProperty(items=track_enum, name="Forward",  get=get_val_T, set=set_val_T)
    ui_mirror: bpy.props.EnumProperty(items=up_enum, name="Mirror",  get=get_val_U, set=set_val_U)
    flip_x: bpy.props.BoolProperty(name="Mirror X Globally")
    swap_l_r: bpy.props.BoolProperty(name="Swap Left <--> Right", update=swapUpdate)

    # Load mappings from a blender configuration text
    def loadMappings(self):
        if self.config_file_name in bpy.data.texts and bpy.data.texts[self.config_file_name].lines[0].body != "":
            mapping = json.loads(bpy.data.texts[self.config_file_name].lines[0].body)
            for machine_id in mapping:
                self.mapping[machine_id] = {'imu': [[{} for x in range(2)] for y in range(2)]}
                for x, imu in enumerate(mapping[machine_id]['imu']):
                    for y, sensor in enumerate(imu):
                        for value in sensor:
                            self.mapping[machine_id]['imu'][x][y][value] = sensor[value]

    # iterate all sensors and call a callback function
    def iterateSensors(self, func):
        for ip in self.sensor_data:
            for bus_num, bus in enumerate(self.sensor_data[ip]['imu']):
                for sensor_num, sensor in enumerate(bus):
                    func(ip, self.machine_ids[ip], bus_num, sensor_num, sensor)

    def setSensorVal(self, ip, bus_num, sens_num, attr, value):
        if 0 <= bus_num <= 1 and 0 <= sens_num <= 1:
            self.sensor_data[ip]["imu"][bus_num][sens_num][attr] = value
            return True
        return False

    # sets initial sensor attributes
    def initPoseFunc(self, ip, machine_id, bus_num, sens_num, sensor):
        # set bone
        if 'bone_name' in self.mapping[machine_id]['imu'][bus_num][sens_num]:
            bone_name = self.mapping[machine_id]['imu'][bus_num][sens_num]['bone_name']
            if self.swap_l_r:
                if 'Left' in bone_name:
                    bone_name = bone_name.replace('Left', 'Right')
                elif 'Right' in bone_name:
                    bone_name = bone_name.replace('Right', 'Left')
                elif '.L' in bone_name:
                    bone_name = bone_name.replace('.L', '.R')
                elif '.R' in bone_name:
                    bone_name = bone_name.replace('.R', '.L')

            if bone_name != '' and bone_name in self.obj.pose.bones:

                bone = self.obj.pose.bones[bone_name]
                self.setSensorVal(ip, bus_num, sens_num, 'bone', bone)
        
                # set matrix
                self.setSensorVal(ip, bus_num, sens_num, 'matrix', bone.matrix.to_quaternion())
        
        # set offset
        if 'position' in self.sensor_data[ip]['imu'][bus_num][sens_num]:
            position = self.sensor_data[ip]['imu'][bus_num][sens_num]['position']
            self.setSensorVal(ip, bus_num, sens_num, 'offset', position)
        else:
            self.setSensorVal(ip, bus_num, sens_num, 'offset', mathutils.Quaternion() )
        
        # set up and forward
        mapping = self.mapping[machine_id]['imu'][bus_num][sens_num]
        if 'forward' in mapping:
            self.setSensorVal(ip, bus_num, sens_num, 'forward', mapping['forward'])        
        if 'mirror' in mapping:
            self.setSensorVal(ip, bus_num, sens_num, 'mirror', mapping['mirror'])

    # Called when a sensor connects
    def addSensor(self, ip, machine_id):
        self.machine_ids[ip] = machine_id
        self.sensor_data[ip] = {'imu': [[{} for x in range(2)] for y in range(2)]}
        
        # add new mapping
        if not machine_id in self.mapping:
            self.mapping[machine_id] = {'imu': [[{} for x in range(2)] for y in range(2)]}
            for x in range(0,2):
                for y in range(0,2):
                    self.mapping[machine_id]['imu'][x][y]['forward'] = 'Y'
                    self.mapping[machine_id]['imu'][x][y]['mirror'] = 'None'
                    self.mapping[machine_id]['imu'][x][y]['bone_name'] = ''
        self.save(self.mapping)
        


register, unregister = bpy.utils.register_classes_factory([MotionCaptureSettings])

if __name__ == "__main__":
    register()