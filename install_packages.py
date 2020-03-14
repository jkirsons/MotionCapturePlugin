import bpy
import sys, subprocess, struct, time, importlib.util

class InstallPackagesOperator(bpy.types.Operator):
    """Install Python Packages"""
    bl_idname = "wm.mocap_install_packages_operator"
    bl_label = "Install Packages"
            
    def execute(self, context):
        self.report({'INFO'}, 'Installing Prerequisites.')
        self.install_all(context)
        return {'FINISHED'}
        
    def install_all(self, context):    

        def install(package):
            subprocess.check_call([bpy.app.binary_path_python, "-m", "pip", "install", package, "--user"])
        
        pacakges = ['torch', 'opencv-python', 'numpy']
        package_names = ['torch', 'cv2', 'numpy']
        for i, package in enumerate(pacakges):
            if importlib.util.find_spec(package_names[i]) == None:
                self.report({'INFO'}, 'Installing: ' + package)
                install(package)
        
        # check that all is ok
        installed = True
        for package in package_names:
            if importlib.util.find_spec(package) == None:
                installed = False
                self.report({'ERROR'}, package + ' could not be installed.')
        if installed:
            self.report({'INFO'}, 'All packages installed')
    
    def download(self):
        import wget
        print('Beginning file download with wget module')
        url = 'http://i3.ytimg.com/vi/J---aiyznGQ/mqdefault.jpg'
        wget.download(url, '/Users/scott/Downloads/cat4.jpg')

register, unregister = bpy.utils.register_classes_factory([InstallPackagesOperator])

if __name__ == "__main__":
    register()