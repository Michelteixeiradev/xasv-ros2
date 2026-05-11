-- migbot_motor_mixer.lua
-- Mixer de motores customizado para o migbot (6 helices assimetricas)
-- Usa FRAME_CLASS=15 (Scripting Matrix)

gcs:send_text(6, "LUA: Mixer V5 Loaded")
--
-- Convencao:
--   throttle = avanco longitudinal (+1 = frente, -1 = re)
--   steering = rotacao yaw (+1 = girar direita, -1 = girar esquerda)
--
-- A matriz de mistura e baseada nas posicoes geometricas dos motores
-- relativas ao centro de massa do migbot.

local SERVO_FUNCTION_MOTOR1 = 94
local SERVO_FUNCTION_MOTOR2 = 95
local SERVO_FUNCTION_MOTOR3 = 96
local SERVO_FUNCTION_MOTOR4 = 97
local SERVO_FUNCTION_MOTOR5 = 98
local SERVO_FUNCTION_MOTOR6 = 99

-- Posicoes dy dos motores (positivo = bombordo/esquerda)
-- Motores a bombordo contribuem positivamente para yaw (girar direita)
-- Motores a estibordo contribuem negativamente para yaw (girar direita)
local DY = {
    -0.649,  -- Motor 1: Estibordo
     0.651,  -- Motor 2: Bombordo
     0.651,  -- Motor 3: Bombordo
    -0.649,  -- Motor 4: Estibordo
     0.651,  -- Motor 5: Bombordo
    -0.649,  -- Motor 6: Estibordo
}

-- Pesos de throttle por motor (todos iguais para avanco reto)
local THROTTLE_WEIGHT = { 1.0, 1.0, 1.0, 1.0, 1.0, 1.0 }

-- Pesos de steering por motor (baseados na distancia lateral dy)
-- Positivo = motor contribui para virar a estibordo (direita)
-- A normalizacao e feita pelo maior valor absoluto de dy
local max_dy = 0.651
local STEERING_WEIGHT = {}
for i = 1, 6 do
    STEERING_WEIGHT[i] = -DY[i] / max_dy
end

local CONTROL_OUTPUT_THROTTLE = 3
local CONTROL_OUTPUT_YAW = 4

local INPUT_EPSILON = 0.02
local last_print_time = 0

local function clamp_unit(value)
    return math.max(-1.0, math.min(1.0, value))
end

local function pwm_to_norm(pwm)
    if not pwm then
        return 0.0
    end
    return (pwm - 1500) / 500.0
end

function update()
    if not arming:is_armed() then
        for i = 1, 6 do
            SRV_Channels:set_output_pwm(SERVO_FUNCTION_MOTOR1 + (i - 1), 1500)
        end
    else
        -- Em AUTO/GUIDED, usa a saida do controlador do Rover quando ela
        -- existe. Em MANUAL, cai para RC direto, que e o que responde a rc 3.
        local rc3 = rc:get_pwm(3)
        local rc1 = rc:get_pwm(1)
        local rc_throttle = pwm_to_norm(rc3)
        local rc_steering = pwm_to_norm(rc1)
        local ap_throttle = vehicle:get_control_output(CONTROL_OUTPUT_THROTTLE)
        local ap_steering = vehicle:get_control_output(CONTROL_OUTPUT_YAW)

        local throttle = rc_throttle
        local steering = rc_steering
        local input_source = "RC"
        if ap_throttle ~= nil or ap_steering ~= nil then
            ap_throttle = ap_throttle or 0.0
            ap_steering = ap_steering or 0.0
            if math.abs(ap_throttle) > INPUT_EPSILON or math.abs(ap_steering) > INPUT_EPSILON then
                throttle = ap_throttle
                steering = ap_steering
                input_source = "AP"
            end
        end

        -- Clamp
        throttle = clamp_unit(throttle)
        steering = clamp_unit(steering)

        local now = millis()
        if now - last_print_time > 2000 then
            gcs:send_text(6, string.format("LUA V5[%s]: th=%.2f, st=%.2f, rc3=%s, rc1=%s",
                input_source, throttle, steering, tostring(rc3), tostring(rc1)))
            last_print_time = now
        end

        for i = 1, 6 do
            local output = throttle * THROTTLE_WEIGHT[i] + steering * STEERING_WEIGHT[i]
            output = clamp_unit(output)
            local pwm = 1500 + (output * 500)
            SRV_Channels:set_output_pwm(SERVO_FUNCTION_MOTOR1 + (i - 1), math.floor(pwm))
        end
    end

    return update, 20  -- 50 Hz
end

return update, 1000  -- Delay inicial de 1s para boot
