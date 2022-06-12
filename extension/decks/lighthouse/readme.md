# Lighthouse Automatic Geometry Estimation Process
The automatic geometry estimation is an **automatic** process of estimating the geometry from multiple posistions inside the flight space.
It performs the same steps as the `multi_bs_geometry_estimation()` but instead of asking to the user to perform the movements of the crazyflie, the drone will move autonomously in the flight space, asking help to the user only if strictly necessary. 
In the best case scenario, the process is able to perform the estimetion fully autonomously, but in the average case the user should help the process.
This process should have better performance in term of precision because the user when moving around the crazyflie, in many situations, the body of the user will cover the IR ray from one of the 2 BS resulting in a high number of invalid samples.
## The configuration
Since the cf will move around autonomously in the flight space and since it cannot know a priori the environment where it will fly, we provide a configuration file that will instruct the crazyflie to perform the most accurate sampling around the whole flight space.
The configuration is done with the [`config.xml`](/config.xml) file and describe the last 3 steps in the estimation process:
 - Origin sample *cannot be configured, it is assumeed to be the starting point of the process (where the user put the cf before starting)*
 - **X axis sample**
 - **XY plane samples**
 - **Space samples**

### The root element
The root element of the configuration is a `<space>` element and must have 1 attribute `default_height` that specify the default height that the drone will use when mooving around.

### X axis configuration
Inside the root element of the xml file you should provide one and only one `<x_axis_point>` element with a required `default_velocity` attribute. Inside the element you should provide one `<x>` element that will describe the x coordinate from the origin that the drone will use to sample the second step.
>This example will move 1 meter forward from the origin with a velocity of 0.5 m/s and then lands for sampling the x-axis.
```xml
<space default_height='0.3'>
    <x_axis_point default_velocity='0.5'>
        <x>1.0</x>
    </x_axis_point>
    ...
</space>
```



### XY plane configuration
At the same level of the x_axis_point element you must provide an `<xy_plane_points>` element that will include the description of 1 to N plane points. Also this element must have a `default_velocity` attribute.
Inside this last element you must provide from 1 to N `<xy_plane_point>` that describe all the points used for sampling on the floor. This last element needs two elements inside: `<x>` and `<y>`.
e.g.
>In this example the cf will move to those points sequentially with a velocity of 0.5 m/s and when arrives at each of those point it lands, sample and restart until the last.
```xml
<space default_height='0.3'>
    ...
    <xy_plane_points default_velocity='0.5'>
        <xy_plane_point>
            <x>1.5</x>
            <y>1.5</y>
        </xy_plane_point>    
        <xy_plane_point>
            <x>-1.5</x>
            <y>1.5</y>
        </xy_plane_point>    
        <xy_plane_point>
            <x>-1.5</x>
            <y>-1.5</y>
        </xy_plane_point>    
        <xy_plane_point>
            <x>1.5</x>
            <y>-1.5</y>
        </xy_plane_point>  
    </xy_plane_points>
    ...
</space>
```



### Space points configuration 
As the previous element this part of the configuration has an `<space_points>` element with the usual `defaulf_velocity` attribute and inside are specified from 1 to N `<waypoint>` each of which will specify an `<x>`, `<y>` and `<z>` elements.
>In this example is represented the first two waypoints that the drone will fly through. Notice that in this case the drone will continuosly samples, this waypoints are meant to be used as guidelines for the trajectory not as sampling points.
```xml
<space default_height='0.3'>
    ...
    <space_points default_velocity='1'>
        <waypoint>
            <x>0.0</x>
            <y>0.0</y>
            <z>0.3</z>
        </waypoint>
        <waypoint>
            <x>1.5</x>
            <y>0.0</y>
            <z>0.3</z>
        </waypoint>
        ....
    </space_points>
</space>
```


## Standard configuration
The [`config.xml`](config.xml) is predefined with a configuration that will cover a fligth area of  3 x 3 x 1.5h meters with **no obstacles** inside and assumning the origin at the center of the 3 x 3 XY plane. 