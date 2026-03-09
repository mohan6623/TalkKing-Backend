import wave, struct, math
obj = wave.open('test.wav','w')
obj.setnchannels(1)
obj.setsampwidth(2)
obj.setframerate(44100)
for i in range(44100):
    value = int(32767.0*math.cos(440.0*math.pi*float(i)/44100.0))
    data = struct.pack('<h', value)
    obj.writeframesraw(data)
obj.close()
