const dump = require('buffer-hexdump');
const WebSocket = require('ws');
const wss = new WebSocket.Server({ port: 8086 });

const states = {
	WAITING: 0,
	FIRST_BYTE: 1,
	WANT_LENGTH: 2,
	IN_PACKET: 3,
	WAIT_CHECKSUM: 4
}

var state = states.WAITING;

var conn

wss.on('connection', function connection(ws) {
  conn = ws
  ws.on('message', function incoming(message) {
    console.log('received: %s', message);
   // ws.send('oh fanks');
  });

  //ws.send('hello');
});

var packet_len
var packet_idx
var checksum
var data = Buffer.alloc(32)
var eeg_data = {
	'power': [0,0,0,0,0,0,0,0],
	'signalQuality': 0,
	'attention': 90,
	'meditation': 0,
	'hasPower': false,
	'rawValue': 0
	}
	
const SerialPort = require('serialport')
const port = new SerialPort('COM5', { baudRate: 9600 })

function clearPacket() {
    for (var i = 0; i < 32; i++) {
        data[i] = 0;
    }
}

function clearEegPower() {
    for(var i = 0; i < 8; i++) {
        eeg_data.power[i] = 0;
    }
}

// for testing only
/*
setInterval(function() {  
    try {
        conn.send(JSON.stringify(eeg_data))
    } catch(error) {

    }
    console.log('Test packet sent!')}, 10000)
*/

function parsePacket(packetData, packetLength){
    // Loop through the packet, extracting data.
    // Based on mindset_communications_protocol.pdf from the Neurosky Mindset SDK.
    // Returns true if passing succeeds
    hasPower = false;
    var rawValue = 0;

    clearEegPower();    // clear the eeg power to make sure we're honest about missing values

    for (var i = 0; i < packetLength; i++) {
    	console.log(i, packetData[i])
        switch (packetData[i]) {
            case 0x2:
                eeg_data.signalQuality = packetData[++i];
                break;
            case 0x4:
                eeg_data.attention = packetData[++i];
                break;
            case 0x5:
                eeg_data.meditation = packetData[++i];
                break;
            case 0x83:
                // ASIC_EEG_POWER: eight big-endian 3-uint8_t unsigned integer values representing delta, theta, low-alpha high-alpha, low-beta, high-beta, low-gamma, and mid-gamma EEG band power values
                // skip length byte
                i++;

                // Extract the values
                for (var j = 0; j < 8; j++) {
                    eeg_data.power[j] = (packetData[++i] << 16) | (packetData[++i] << 8) | packetData[++i];
                }

                eeg_data.hasPower = true;
                break;
            case 0x80:
                i++;
                eeg_data.rawValue = (packetData[++i] << 8) | packetData[++i];
                break;
            default:
                // Broken packet ?
                parseSuccess = false;
                break;
        }
    }
    console.log(eeg_data)
    try {
    	conn.send(JSON.stringify(eeg_data))
    } catch(error) {
    
    }
}


port.on('data', function data(chunk)  {
 	for(var i=0;i<chunk.length;++i) {
 		if(state == states.IN_PACKET) {
 			data[packet_idx++] = chunk[i]
 			if(packet_idx==packet_len) {
 				state = states.WAIT_CHECKSUM
 			}
 			checksum += chunk[i]
 		} else if(chunk[i]==0xaa && state == states.WAITING) {
 			state = states.FIRST_BYTE;
 		} else if (chunk[i]==0xaa && state == states.FIRST_BYTE) {
 			state = states.WANT_LENGTH;
 			console.log('got header')
 		} else if(state==states.WANT_LENGTH) {
 			packet_len = chunk[i]
 			if(packet_len>32 || packet_len == 0) {
 				console.log('Invalid packet length '+packet_len)
 				state = states.WAITING
 			} else {
 				state = states.IN_PACKET
 			}
 			packet_idx = 0
 			checksum = 0 
 		} else if(state==states.WAIT_CHECKSUM) {
 			if(255-(checksum%256) != chunk[i]) {
 				console.log('Bad checksum')
 			} else {
 				console.log('parsing')
 				parsePacket(data, packet_idx)
 				console.log('clearing')
 				clearPacket()
 				console.log(eeg_data)
 				packet_idx = 0;
 				state = states.WAITING
 			}
 		}
 	}
});

