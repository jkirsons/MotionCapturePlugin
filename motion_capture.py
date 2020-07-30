import bpy, mathutils, math, json, copy
import select, socket, sys, subprocess, struct, time, importlib.util
from . import settings

class MotionCaptureOperator(bpy.types.Operator):
    """Start Motion Capture"""
    bl_idname = "wm.mocap_operator"
    bl_label = "Motion Capture Operator"
    bl_options = {'REGISTER'}

    # Framerate Counter
    frame = 0
    start = time.time()
    start_rec_time = 0
    sensors_connected = []

    frame_number = 0
    recording = {}
    buttons = {}
    
    # Socket Server
    inputs = []
    server = None  
    
    debug_quats = [[] for x in range(10)]

    def updateBone(self, ip, machine_id, bus_num, sens_num, sensor):
        settings = bpy.context.scene.mc_settings
        if 'bone' in sensor:
            bone = sensor['bone']
            if "mirror"in sensor and "forward" in sensor and "offset"in sensor and "matrix" in sensor and "position" in sensor:
                forward_vec = settings.dir_enum[sensor['forward']]
                forward = mathutils.Vector((0,1,0)).rotation_difference(forward_vec) 

                position1 = sensor['offset'].conjugated() @ sensor['position']

                # Mirror sensor axes
                if sensor['mirror'] == 'X':    
                    position1.x *= -1
                    position1.w *= -1
                if sensor['mirror'] == 'Y':    
                    position1.y *= -1
                    position1.w *= -1
                if sensor['mirror'] == 'Z':    
                    position1.z *= -1
                    position1.w *= -1   
                # Global Mirror X    
                if settings.flip_x:    
                    position1.x *= -1
                    position1.w *= -1    
                # Swap Left <--> Right 
                if settings.swap_l_r:    
                    position1.y *= -1
                    position1.x *= -1
                    position1.w *= -1

                position2 = forward @ position1
                position3 = position2 @ (forward.rotation_difference(sensor['matrix']))

                (translation, rotatation, scale) = bone.matrix.decompose()
                bone.matrix = mathutils.Matrix.Translation(translation) @ position3.to_matrix().to_4x4() 
                
                if bpy.context.scene.mc_settings.start_rec:
                    #bone.keyframe_insert(data_path="rotation_quaternion")
                    if not bone in self.recording:
                        self.recording[bone] = []
                    # animation records local rotations
                    #self.recording[bone].append([self.frame_number, sensor['matrix'].rotation_difference(bone.matrix.to_quaternion())])
                    quat = bone.matrix_basis.to_quaternion()
                    self.recording[bone].append([self.frame_number, quat])

                if (settings.machine_ids[ip], bus_num, sens_num) == settings.keyToSensors(settings.selected_id):
                    index = 0
                    self.debugQuat(0, index, forward)
                    self.debugQuat(1, index, sensor['matrix'])
                    self.debugQuat(2, index, sensor['position'])
                    self.debugQuat(3, index, position1)
                    self.debugQuat(4, index, position2)
                    self.debugQuat(5, index, position3)
    
    def debugQuat(self, num, index, quat):
        settings = bpy.context.scene.mc_settings
        while len(self.debug_quats[num]) <= index:
            if "Template_"+str(num)+"_"+str(index) in bpy.data.objects:
                self.debug_quats[num].append(bpy.data.objects["Template_"+str(num)+"_"+str(index)])
            else:
                ob = settings.template.copy()
                ob.name = "Template_"+str(num)+"_"+str(index)
                bpy.context.collection.objects.link(ob)
                self.debug_quats[num].append(ob)
        self.debug_quats[num][index].matrix_world = quat.to_matrix().to_4x4()
        self.debug_quats[num][index].location[0] = -1 
        self.debug_quats[num][index].location[1] = -num - 1
    
    # The main "loop"
    def modal(self, context, event):
        for id in self.buttons:
            if self.buttons[id] == 1 and id in context.scene.mc_settings.button_map:
                if context.scene.mc_settings.button_map[id] == 1: #"T-Pose":
                    bpy.ops.wm.mocap_set_tpose_operator(timer=3)
                if context.scene.mc_settings.button_map[id] == 2: #"Start/Stop":
                    context.scene.mc_settings.start_rec = not context.scene.mc_settings.start_rec
                self.buttons[id] = 0
        
        if (not context.scene.mc_settings.start_rec or not context.scene.mc_settings.start) and self.start_rec_time != 0:
            self.saveRecording()

        if context.scene.mc_settings.start_rec and self.start_rec_time == 0:
            self.start_rec_time = time.time()

        if not context.scene.mc_settings.start:
            self.cancel(context)
            return {'CANCELLED'}

        if event.type == 'TIMER':    
            if len(self.inputs) == 0: self.inputs = [self.server]     
            while True:
                readable, writable, exceptional = select.select(self.inputs, [], self.inputs, 0)
                for s in readable:
                    if s is self.server:
                        print("Accepting Connection")
                        connection, client_address = s.accept()
                        connection.setblocking(0)
                        self.inputs.append(connection)
                    else:
                        data = s.recv(11)
                        peer_ip = str(s.getpeername()[0])
                        if data: 
                            # Quaternion
                            if data[0] == 0 and len(data) == 11:
                                quat = self.scaled_tuple(scale=1/(1 << 14), buf=data[3:11])  # (w, x, y, z)
                                if bpy.context.scene.mc_settings.setSensorVal(peer_ip, data[1], data[2], "position", mathutils.Quaternion(quat).normalized()):
                                    if not str(peer_ip)+str(data[1])+str(data[2]) in self.sensors_connected:
                                        self.sensors_connected.append(str(peer_ip)+str(data[1])+str(data[2]))
                            # Unique Identifier
                            elif data[0] == 9 and len(data) == 7:
                                bpy.context.scene.mc_settings.addSensor(peer_ip, str(data[1:8]))
                            # Button pressed
                            elif data[0] == 2 and data[1] == 1:
                                self.buttons[bpy.context.scene.mc_settings.machine_ids[peer_ip]] = 1
                                print("Button: " + str(peer_ip))
                            else:
                                print("Invalid Transaction ID: " + str(data[0]) + " Length: " + str(len(data)) + " Date: " + str(time.time()))

                            self.frame += 1
                                                         
                        else:
                            print("no data")
                            self.inputs.remove(s)
                            s.close()
                            break
                            
                for s in exceptional:
                    print("exception")
                    self.inputs.remove(s)
                    s.close()
                    break
                if len(readable) == 0: break

        if context.scene.mc_settings.start_rec:
            time_now = (time.time() - self.start_rec_time) * bpy.context.scene.render.fps
            time_rem, time_int = math.modf(time_now)
            if len(self.recording) > 0 and time_int in self.recording[next(iter(self.recording))] and time_rem > 0.8:
                self.frame_number = time_int + 1
            elif len(self.recording) > 0 and time_int > 1 \
                and not time_int-1 in self.recording[next(iter(self.recording))] \
                and time_rem < 0.2:
                self.frame_number = time_int - 1
            else:
                self.frame_number = time_int
            context.scene.mc_settings.frame_number = self.frame_number

        # Update bone rotations
        bpy.context.scene.mc_settings.iterateSensors(self.updateBone)

        if self.frame > 300:
            time_diff = time.time() - self.start
            self.start = time.time()
            if len(self.sensors_connected) > 0 and time_diff > 0:
                bpy.context.scene.mc_settings.fps = self.frame / time_diff / len(self.sensors_connected)
            self.frame = 1

        return {'PASS_THROUGH'}
    
    def execute(self, context):
        bpy.app.handlers.frame_change_pre.append(self.extend_playback)
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.setblocking(0)
        try:
            self.server.bind((self.get_ip_address(), context.scene.mc_settings.port))
        except OSError:
            self.report({'ERROR'}, 'Socket in use - please try again')
            self.cancel(context)
            context.scene.mc_settings.start = False
            return {'CANCELLED'}
        self.server.listen(5)
        
        print("Starting")
        
        # Load settings
        context.scene.mc_settings.loadMappings()
        context.scene.mc_settings.iterateSensors(context.scene.mc_settings.initPoseFunc)
        
        bpy.context.scene.mc_settings.fps = 0.0
        self.start_rec_time = 0
        
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.01, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}


    def saveRecording(self):
        recNumber = 1
        while 'Recording'+str(recNumber) in bpy.data.actions:
            recNumber += 1

        a = bpy.data.actions.new('Recording'+str(recNumber))

        for bone in self.recording:
            for i in range(0,4):
                fc = a.fcurves.new('pose.bones["'+bone.name+'"].rotation_quaternion', index=i, action_group=bone.name)
                fc.keyframe_points.add(count=len(self.recording[bone]))
                vals = [v[1][i] for v in self.recording[bone]]
                keys = [v[0] for v in self.recording[bone]]
                fc.keyframe_points.foreach_set("co", [x for co in zip(keys, vals) for x in co])
                fc.update()

        self.recording.clear()
        self.start_rec_time = 0

    def cancel(self, context):
        # close open sockets
        for sock in self.inputs:
            sock.close()
        self.inputs.clear()

        wm = context.window_manager
        if hasattr(self, '_timer'):
            wm.event_timer_remove(self._timer)
        self.server.close()
        print("Stopping")
        context.scene.mc_settings.fps = 0.0
        self.sensors_connected.clear()
        
        
    def get_ip_address(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip

    def scaled_tuple(self, scale, buf=bytearray(8), fmt='<hhhh'):
        return list(b*scale for b in struct.unpack(fmt, buf))

    def reconnect(self, s):
        print("Reconnecting...")
        conn, addr = s.accept()
        print('Connected by', addr)
        return conn, addr

    def extend_playback(self, scene, last):
        if scene.frame_current >= scene.frame_end-100 and scene.mc_settings.start:
            scene.frame_end = scene.frame_end+100
            #bpy.ops.screen.animation_cancel(restore_frame=False)    

register, unregister = bpy.utils.register_classes_factory([MotionCaptureOperator])

if __name__ == "__main__":
    register()
