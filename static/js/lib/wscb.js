var ipc, WebSocket;

class WebSockets_Callback {
  constructor(options) {
    
    this.triggers = {}
    this.expectations = {}
    this.clients = []
    
    this.options = {
      verbose: true, //will log some messages to the console
      asClient: false, //will setup WSCB as a client. Browser incompatible.
      proto: 'ws://', // MOD: Added proto option.
      address: '127.0.0.1',
      port: 7081,
      path: '/ws',  // MOD: Added path option.
      onOpen: undefined,
      onError: undefined,
      onListening: undefined,
      onUnexpectedMessage: console.log
    }
    this.options = {...this.options, ...options}
    
    if (((typeof process !== 'undefined') && (process.release.name === 'node')) && (this.options.asClient == undefined || this.options.asClient == false))
      this.setupAsServer()
    else
      this.setupAsClient()
    
    
    if (this.options.asElectron) {
      
      
      if (this.options.asClient) ipc = require('electron').ipcRenderer
      else ipc = require('electron').ipcMain
      
      if (!this.options.asClient) {
        const {webContents} = require('electron')
        this.sendData = msg => {
          var wcs = webContents.getAllWebContents()
          for (var i in wcs) {
            var wc = wcs[i]
            wc.send('wscb', msg)
          }
        }
        
        ipc.on('wscb', (event, arg) => {
          console.log(event.sender.getOwnerBrowserWindow())
          
          this.handleMessage(this, arg, {
            send: (msg) => {
              event.reply('wscb', msg)
            }
          })
        })
        return
      }
      
      
      this.sendData = msg => {
        ipc.send('wscb', msg)
      }
      ipc.on('wscb', (event, arg) => {
        this.handleMessage(this, arg, {
          send: (msg) => {
            ipc.send('wscb', msg)
          }
        })
      })
    } else {
      //WebSocket = require('ws');
    }
    
    
  }
  
  log(str) {
    if (this.options.verbose) console.log('[ WebSockets-Callback ]  ' + str);
  }
  
  setupAsServer() {
    this.ws_types = {expector: '#s', responder: '#c'};
    
    var t = this;
    
    if (this.options.asElectron) return
    
    this.ws = new WebSocket.Server({port: this.options.port});
    
    this.log('Starting server @ port ' + t.options.port + '...')
    this.ws.on('connection', function (conn) {
      
      var cuid = 'c:' + Date.now();
      conn.id = cuid;
      t.clients[cuid] = conn;
      
      if (t.options.onOpen != null) t.options.onOpen(conn)
      conn.on('message', function (message) {
        var json = JSON.parse(message);
        if (json.puid != undefined) {
          t.handleMessage(t, json, conn)
        } else {
          if (t.options.onUnexpectedMessage != undefined) t.options.onUnexpectedMessage(conn, json)
        }
      }).on('close', function (event) {
        if (t.options.onClose != undefined) t.options.onClose(event);
        console.log('Client disconnected!');
        delete t.clients[this.id];
      });
      
    }).on('error', function (conn, error) {
      if (t.options.onError != null) t.options.onError(conn, error)
      console.log('[WS ERROR]')
      console.log(error)
    }).on('listening', function () {
      if (t.options.onListening != null) t.options.onListening()
      t.log('Server listening @ port ' + t.options.port);
    });
    
    
  }
  
  setupAsClient() {
    this.ws_types = {expector: '#c', responder: '#s'};
    
    var t = this;
    
    if (this.options.asElectron) return
    
    this.log('Connecting to server ' + this.options.proto + this.options.address + ' @ ' + this.options.port + this.options.path)
    this.ws = new WebSocket(this.options.proto + this.options.address + ':' + this.options.port + this.options.path);
    
    this.ws.onopen = function (event) {
      if (t.options.onOpen !== undefined) t.options.onOpen();
      t.log('Connected to server ' + t.options.proto + t.options.address + ' @ ' + t.options.port)
    };
    
    this.ws.onmessage = function (event) {
      //console.log('ws.onmessage', event)
      var json = JSON.parse(event.data);
      if (json.puid !== undefined) {
        t.handleMessage(t, json)
      } else {
        if (t.options.onUnexpectedMessage !== undefined) t.options.onUnexpectedMessage(event)
      }
    }
    
    this.ws.onerror = function (event) {
      if (t.options.onError != null) t.options.onError(event.error)
      console.log('[WS ERROR]')
      console.log(event.error)
    }
    
    this.ws.onclose = function (event) {
      if (t.options.onClose !== undefined) t.options.onClose(event);
    };
  }
  
  
  handleMessage(t, json, conn = undefined) {
    
    var sender = json.puid.substr(0, 2);
    if (sender === this.ws_types.expector)
      t.handleResponse(t, json, conn)
    else if (sender === this.ws_types.responder)
      t.handleExpectation(t, json, conn)
  }
  
  handleResponse(t, json, conn = undefined) {
    //server responded to a message that we expected to have a response
    if (t.expectations[json.puid] !== undefined) {
      if (json.progress === undefined || json.progress === 100) {
        t.expectations[json.puid].onResponse(json);
        delete t.expectations[json.puid];
      } else {
        t.expectations[json.puid].onProgress(json);
      }
    }
  }
  
  handleExpectation(t, json, conn = undefined) {
    if (t.triggers.hasOwnProperty(json.cmd)) {
      t.triggers[json.cmd].doHandle(json, function (response) {
        if (response.puid === undefined) response.puid = json.puid;
        t.send(response, undefined, undefined, conn);
      })
    }
  }
  
  
  send(message, onResponse = undefined, onProgress = undefined, conn = undefined) {
    if (message === undefined) return;
    
    if (onResponse !== undefined) {
      var puid = this.ws_types.expector + Math.random(); //Date.now();
      this.expectations[puid] = {onResponse: onResponse, onProgress: onProgress};
      message.puid = puid;
    }
    
    if (conn !== undefined) {
      if (this.options.asElectron) conn.send(message)
      else conn.send(JSON.stringify(message));
    } else {
      if (this.ws_types.expector === '#s') {
        if (this.options.asElectron) {
          this.sendData(message)
        } else {
          for (var i = 0; i < Object.keys(this.clients).length; i++) {
            var key = Object.keys(this.clients)[i];
            this.clients[key].send(JSON.stringify(message));
          }
        }
      } else {
        if (this.options.asElectron) this.sendData(message)
        else this.ws.send(JSON.stringify(message));
      }
    }
  }
  
  simple(msg, onResponse = undefined, t = undefined) {
    if (conn !== undefined || this.options.asElectron) {
      conn.send({cmd: msg});
    } else {
      if (this.ws_types.expector === '#s') {
        for (var i = 0; i < Object.keys(this.clients).length; i++) {
          var key = Object.keys(this.clients)[i];
          this.clients[key].send({cmd: msg});
        }
      } else {
        this.ws.send({cmd: msg});
      }
    }
  }
  
  on(command, doHandle) {
    this.triggers[command] = {doHandle: doHandle}
  }
  
  close() {
    this.ws.close()
  }
}


var WebSocket;

if ((typeof process !== 'undefined') && (process.release.name === 'node')) {
  WebSocket = require('ws');
  module.exports = WebSockets_Callback;
}
