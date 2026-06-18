obs = obslua

-- Global state
output_file = ""
recording_start_time = 0
is_recording = false
partida_start_time = nil

-- Description displayed in OBS Scripts window
function script_description()
    return [[
<h2>Video Highlight Marker</h2>
<p>Marca momentos importantes durante la grabación:</p>
<ul>
    <li><b>F9</b>: Marcar highlight (momento épico)</li>
    <li><b>F10</b>: Inicio de partida</li>
    <li><b>F11</b>: Fin de partida</li>
</ul>
<p>Genera timestamps.json en la carpeta del video grabado.</p>
]]
end

-- Properties (settings) shown in OBS
function script_properties()
    local props = obs.obs_properties_create()
    
    obs.obs_properties_add_path(props, "output_folder", "Carpeta de salida", obs.OBS_PATH_DIRECTORY, "", "")
    obs.obs_properties_add_int(props, "highlight_duration", "Duración highlight (segundos)", 30, 120, 5)
    
    return props
end

-- Default settings
function script_defaults(settings)
    obs.obs_data_set_default_string(settings, "output_folder", "")
    obs.obs_data_set_default_int(settings, "highlight_duration", 60)
end

-- Update settings
function script_update(settings)
    output_folder = obs.obs_data_get_string(settings, "output_folder")
    highlight_duration = obs.obs_data_get_int(settings, "highlight_duration")
end

-- Get current recording time in seconds
function get_recording_time()
    if not is_recording then
        return 0
    end
    local current_time = os.time()
    return current_time - recording_start_time
end

-- Write timestamp to JSON file
function write_timestamp(timestamp_type, duration)
    local timestamp = get_recording_time()
    
    if timestamp <= 0 then
        print("[Marker] No hay grabación activa")
        return
    end
    
    -- Determine output file path
    local file_path = output_file
    if file_path == "" then
        print("[Marker] ERROR: No se pudo determinar la ruta del archivo")
        return
    end
    
    -- Read existing data
    local existing_data = {}
    local file = io.open(file_path, "r")
    if file then
        local content = file:read("*all")
        file:close()
        
        -- Parse JSON manually (Lua doesn't have native JSON)
        if content ~= "" and content ~= "[]" then
            -- Remove brackets and split by },
            content = content:gsub("^%[", ""):gsub("%]$", "")
            for entry in content:gmatch("{[^}]+}") do
                table.insert(existing_data, entry)
            end
        end
    end
    
    -- Create new entry
    local new_entry
    if duration then
        new_entry = string.format('{"time": %.2f, "type": "%s", "duration": %d}', 
                                   timestamp, timestamp_type, duration)
    else
        new_entry = string.format('{"time": %.2f, "type": "%s"}', 
                                   timestamp, timestamp_type)
    end
    
    table.insert(existing_data, new_entry)
    
    -- Write back to file
    file = io.open(file_path, "w")
    if file then
        file:write("[\n  ")
        file:write(table.concat(existing_data, ",\n  "))
        file:write("\n]")
        file:close()
        print(string.format("[Marker] ✓ %s marcado en %.2fs", timestamp_type, timestamp))
    else
        print("[Marker] ERROR: No se pudo escribir el archivo")
    end
end

-- Hotkey callbacks
function mark_highlight(pressed)
    if not pressed then return end
    write_timestamp("highlight", highlight_duration)
end

function mark_partida_start(pressed)
    if not pressed then return end
    partida_start_time = get_recording_time()
    write_timestamp("partida_start", nil)
end

function mark_partida_end(pressed)
    if not pressed then return end
    local duration = nil
    if partida_start_time then
        duration = get_recording_time() - partida_start_time
        partida_start_time = nil
    end
    write_timestamp("partida_end", duration)
end

-- Recording event callbacks
function on_event(event)
    if event == obs.OBS_FRONTEND_EVENT_RECORDING_STARTED then
        is_recording = true
        recording_start_time = os.time()
        
        -- Get output file path from OBS
        local output = obs.obs_frontend_get_recording_output()
        if output then
            local settings = obs.obs_output_get_settings(output)
            local path = obs.obs_data_get_string(settings, "path")
            
            -- If path is empty, try url (for different output types)
            if path == "" then
                path = obs.obs_data_get_string(settings, "url")
            end
            
            obs.obs_data_release(settings)
            obs.obs_output_release(output)
            
            if path ~= "" then
                -- Replace video extension with .json
                output_file = path:gsub("%.%w+$", "") .. "_timestamps.json"
                
                -- Initialize empty JSON file
                local file = io.open(output_file, "w")
                if file then
                    file:write("[]")
                    file:close()
                    print("[Marker] Iniciado: " .. output_file)
                end
            else
                print("[Marker] WARNING: No se pudo obtener la ruta del video")
            end
        end
        
        partida_start_time = nil
        
    elseif event == obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED then
        is_recording = false
        print("[Marker] Grabación finalizada")
        output_file = ""
    end
end

-- Register hotkeys
function script_load(settings)
    -- Register hotkeys
    obs.obs_hotkey_register_frontend("mark_highlight", "Marcar Highlight (F9)", mark_highlight)
    obs.obs_hotkey_register_frontend("mark_partida_start", "Inicio de Partida (F10)", mark_partida_start)
    obs.obs_hotkey_register_frontend("mark_partida_end", "Fin de Partida (F11)", mark_partida_end)
    
    -- Register event callback
    obs.obs_frontend_add_event_callback(on_event)
    
    print("[Marker] Script cargado correctamente")
end

function script_unload()
    print("[Marker] Script descargado")
end
