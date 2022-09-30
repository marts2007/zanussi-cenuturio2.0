# ZANUSSI Home Assistant component
Currently works with Centurio2.0<br>
put zanussiwh folder to config/custom_components/ <br>
add configuration option to configuration.yaml

```
  water_heater:
  - platform: zanussiwh
    name: Some name here
    unique_id: some_uniq_name
    host: ip_address_here
```



In order to get status updates, I have used mikrotiks`s packet sniffer with streaming option enabled (port 37008)
