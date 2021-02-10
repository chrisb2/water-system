# Window solution
import weather
import urequests
import ure

chunkSize = 30
windowSize = chunkSize * 2
window = bytearray(windowSize)
emptyChunk = bytearray(chunkSize)

start_regex = ure.compile(b'timeseries')
continue_regex = ure.compile(b'\},\{')
hour_regex = ure.compile(b'next_1_hours')
precip_regex = ure.compile(b'precipitation_amount\":(\d+\.\d)')
time_regex = ure.compile(b'time\":\"(\d+-\d+-\d+)T')

periodFound = False
hourFound = False
precipFound = False
timeFound = False

with urequests.get(weather._FORECAST_URL,
                   headers=weather._FORECAST_HEADER) as response:
    print('HTTP status: %d' % response.status_code)
    if response.status_code == 200 or response.status_code == 203:
        for chunk in response.iter_content(chunkSize):
            # Populate window
            memoryview(window)[0:chunkSize] =\
                memoryview(window)[chunkSize:windowSize]
            if len(chunk) == chunkSize:
                memoryview(window)[chunkSize:windowSize] = chunk
            else:
                # last chunk is short
                memoryview(window)[chunkSize:windowSize] = emptyChunk
                memoryview(window)[chunkSize:chunkSize+len(chunk)] = chunk
            # print(window)
            windowBytes = bytes(memoryview(window))  # regex requires bytes
            # Gather precipitation data
            if continue_regex.search(windowBytes) or\
               start_regex.search(windowBytes):
                periodFound = True
            if periodFound and hour_regex.search(windowBytes):
                hourFound = True
            if periodFound and not timeFound:
                timeGroup = time_regex.search(windowBytes)
                if timeGroup:
                    timeFound = True
                    time = timeGroup.group(1)
            if hourFound and not precipFound:
                precipGroup = precip_regex.search(windowBytes)
                if precipGroup:
                    precipFound = True
                    mm = precipGroup.group(1)
            if timeFound and precipFound:
                periodFound = False
                hourFound = False
                timeFound = False
                precipFound = False
                print(time.decode(), mm.decode())
