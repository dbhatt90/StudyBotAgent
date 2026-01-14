"""
app.py - Enhanced with Connection Reset & Status Display

New Features:
1. Visual connection status with indicators
2. "New Conversation" button
3. Session info display (new vs restored)
4. Reconnection toasts
5. Debug panel (optional)
"""

import dash
from dash import html, dcc, Input, Output, State
from flask import Flask
import os
from dotenv import load_dotenv
from Websocket import init_socketio

load_dotenv()

server = Flask(__name__)
server.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'test-secret-key')

socketio = init_socketio(server)

app = dash.Dash(__name__, server=server, suppress_callback_exceptions=True)

# Enhanced Layout with Connection Controls
app.layout = html.Div([
    # Header with Connection Status
    html.Div([
        html.Div([
            html.H1('🤖 StudyBot Assistant', style={'margin': 0}),
            html.Div(id='session-type', 
                    children='',
                    style={'fontSize': '12px', 'opacity': '0.9', 'marginTop': '5px'})
        ]),
        
        # Connection Status & Controls
        html.Div([
            # Status Indicator
            html.Div([
                html.Span(id='connection-indicator', 
                         children='●',
                         style={'fontSize': '24px', 'marginRight': '8px'}),
                html.Div([
                    html.Div(id='connection-status', 
                            children='Connecting...',
                            style={'fontSize': '14px', 'fontWeight': 'bold'}),
                    html.Div(id='connection-details',
                            children='',
                            style={'fontSize': '11px', 'opacity': '0.8'})
                ])
            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '10px'}),
            
            # Action Buttons
            html.Div([
                html.Button('🔄 New Chat',
                           id='new-conversation-btn',
                           n_clicks=0,
                           style={
                               'background': 'rgba(255,255,255,0.2)',
                               'color': 'white',
                               'border': '1px solid white',
                               'padding': '8px 16px',
                               'borderRadius': '6px',
                               'cursor': 'pointer',
                               'fontSize': '13px',
                               'marginRight': '8px'
                           }),
                html.Button('📊 Status',
                           id='show-status-btn',
                           n_clicks=0,
                           style={
                               'background': 'rgba(255,255,255,0.2)',
                               'color': 'white',
                               'border': '1px solid white',
                               'padding': '8px 16px',
                               'borderRadius': '6px',
                               'cursor': 'pointer',
                               'fontSize': '13px'
                           })
            ], style={'display': 'flex'})
        ])
    ], style={
        'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        'padding': '20px',
        'color': 'white',
        'boxShadow': '0 2px 10px rgba(0,0,0,0.1)',
        'display': 'flex',
        'justifyContent': 'space-between',
        'alignItems': 'center'
    }),
    
    # Toast Container (for notifications)
    html.Div(id='toast-container', 
            children=[],
            style={
                'position': 'fixed',
                'top': '90px',
                'right': '20px',
                'zIndex': 9999
            }),
    
    # Main container
html.Div([
    # Progress Card (keep as-is above)
    html.Div([
        html.Div([
            html.Span('📊 Form Progress', 
                     style={'fontSize': '16px', 'fontWeight': 'bold', 'color': '#333'}),
            html.Span(id='progress-percentage', 
                     children='0%',
                     style={'fontSize': '24px', 'fontWeight': 'bold', 'color': '#667eea'})
        ], style={'display': 'flex', 'justifyContent': 'space-between', 'marginBottom': '10px'}),
        
        # Progress bar
        html.Div([
            html.Div(id='progress-bar',
                    style={
                        'height': '8px',
                        'background': '#667eea',
                        'borderRadius': '4px',
                        'width': '0%',
                        'transition': 'width 0.5s ease'
                    })
        ], style={
            'height': '8px',
            'background': '#e0e0e0',
            'borderRadius': '4px',
            'marginBottom': '15px'
        }),
        
        # Field status
        html.Div([
            html.Div(id='filled-fields-count', 
                    children='0 fields filled',
                    style={'color': '#4caf50', 'fontWeight': '500'}),
            html.Div(id='empty-fields-count',
                    children='8 fields remaining',
                    style={'color': '#ff9800', 'fontWeight': '500'})
        ], style={'display': 'flex', 'justifyContent': 'space-between', 'fontSize': '14px'}),
        
        # Conversation ID (for debugging)
        html.Div(id='conversation-id-display',
                children='',
                style={
                    'marginTop': '10px',
                    'padding': '8px',
                    'background': '#f5f5f5',
                    'borderRadius': '4px',
                    'fontSize': '11px',
                    'color': '#666',
                    'fontFamily': 'monospace',
                    'display': 'none'
                })
    ], style={
        'background': 'white',
        'padding': '20px',
        'borderRadius': '10px',
        'boxShadow': '0 2px 8px rgba(0,0,0,0.1)',
        'marginBottom': '20px'
    }),

    # Chat + Form container (row layout)
    html.Div([
        # Chat container
        html.Div([
            html.Div(id='chat-messages',
                    style={
                        'height': '500px',
                        'overflowY': 'auto',
                        'padding': '20px',
                        'background': '#f8f9fa',
                        'borderRadius': '10px 10px 0 0',
                        'display': 'flex',
                        'flexDirection': 'column',
                        'gap': '15px'
                    }),
            
            # Input area
            html.Div([
                dcc.Textarea(
                    id='message-input',
                    placeholder='Type your message here...',
                    style={
                        'width': '100%',
                        'minHeight': '60px',
                        'maxHeight': '120px',
                        'border': 'none',
                        'padding': '15px',
                        'fontSize': '15px',
                        'resize': 'none',
                        'outline': 'none',
                        'fontFamily': 'inherit'
                    }
                ),
                html.Button('Send',
                           id='send-btn',
                           n_clicks=0,
                           style={
                               'background': '#667eea',
                               'color': 'white',
                               'border': 'none',
                               'padding': '15px 30px',
                               'borderRadius': '8px',
                               'cursor': 'pointer',
                               'fontSize': '16px',
                               'fontWeight': 'bold',
                               'transition': 'background 0.3s'
                           })
            ], style={
                'display': 'flex',
                'alignItems': 'flex-end',
                'gap': '10px',
                'background': 'white',
                'padding': '15px',
                'borderRadius': '0 0 10px 10px',
                'boxShadow': '0 -2px 10px rgba(0,0,0,0.05)'
            })
        ], style={
            'flex': '2',  # Takes 2/3 of the width
            'background': 'white',
            'borderRadius': '10px',
            'boxShadow': '0 2px 8px rgba(0,0,0,0.1)',
            'overflow': 'hidden'
        }),

        # Dynamic form container
        html.Div(id='dynamic-form', style={
            'flex': '1',  # Takes 1/3 of the width
            'background': 'white',
            'padding': '20px',
            'borderRadius': '10px',
            'boxShadow': '0 2px 8px rgba(0,0,0,0.1)',
            'marginLeft': '20px',  # Space between chat and form
            'overflowY': 'auto',
            'maxHeight': '580px'
        })
    ], style={
        'display': 'flex',
        'gap': '0',
        'marginBottom': '20px'
    }),

    # Quick actions (keep as-is)
    html.Div(id='quick-actions', 
            children=[],
            style={'marginTop': '15px'})
], style={
    'maxWidth': '1200px',
    'margin': '0 auto',
    'padding': '20px'
}),

    
    # Hidden stores
    dcc.Store(id='conversation-id', storage_type='local'),
    dcc.Store(id='messages-store', data=[]),
    dcc.Store(id='agent-state', data={}),
    dcc.Interval(id='init-interval', interval=1000, n_intervals=0, max_intervals=1)
    
], style={
    'fontFamily': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    'background': '#f0f2f5',
    'minHeight': '100vh'
})

# Enhanced Socket.IO client with connection management
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>StudyBot Assistant</title>
        {%css%}
        <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
        <style>
            #chat-messages::-webkit-scrollbar {
                width: 8px;
            }
            #chat-messages::-webkit-scrollbar-track {
                background: #f1f1f1;
                border-radius: 10px;
            }
            #chat-messages::-webkit-scrollbar-thumb {
                background: #c1c1c1;
                border-radius: 10px;
            }
            #send-btn:hover {
                background: #5568d3 !important;
            }
            .message-enter {
                animation: slideIn 0.3s ease-out;
            }
            @keyframes slideIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            @keyframes slideInRight {
                from { opacity: 0; transform: translateX(50px); }
                to { opacity: 1; transform: translateX(0); }
            }
            @keyframes slideOutRight {
                from { opacity: 1; transform: translateX(0); }
                to { opacity: 0; transform: translateX(50px); }
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
        
        <script>
            // ========================================
            // CONNECTION STATE MANAGEMENT
            // ========================================
            console.log("Hello");
            const socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);
            console.log(location.protocol, document.domain, location.port);
            
            let connectionState = {
                socket_connected: false,
                agent_joined: false,
                conversation_id: null,
                restored: false,
                progress_pct: 0
            };
            
            let conversationHistory = [];  
            let historyDisplayed = false;   
            let lastConnectionState = false;
            
            // Get or create conversation ID
            let conversationId = localStorage.getItem('conversationId');
            if (!conversationId) {
                conversationId = 'conv-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
                localStorage.setItem('conversationId', conversationId);
                console.log('🆕 New conversation:', conversationId);
            } else {
                console.log('♻️ Existing conversation:', conversationId);
            }
            
            // Display conversation ID
            updateConversationIdDisplay();
            
            // ========================================
            // SOCKET EVENT HANDLERS
            // ========================================
            
            socket.on('connect', function() {
                console.log('✅ WebSocket Connected');
                connectionState.socket_connected = true;
                
                // Show reconnection toast if previously disconnected
                if (!lastConnectionState) {
                    showToast('✅ Reconnected!', 'success');
                }
                lastConnectionState = true;
                
                updateConnectionStatus();
                
                // Join conversation
                socket.emit('join_conversation', {conversation_id: conversationId});
            });
            
            socket.on('disconnect', function() {
                console.log('❌ WebSocket Disconnected');
                connectionState.socket_connected = false;
                connectionState.agent_joined = false;
                lastConnectionState = false;
                
                updateConnectionStatus();
                showToast('❌ Connection lost. Reconnecting...', 'warning');
            });



            
            socket.on('joined_conversation', function(data) {
            console.log('✅ Joined conversation:', data);
            connectionState.agent_joined = true;
            connectionState.conversation_id = data.conversation_id;
            
            // Store conversation history
            conversationHistory = data.conversation_history || [];
            console.log('📜 Received conversation history:', conversationHistory.length, 'messages');
            
            // Check if this is a restored session
            const isRestored = data.agent_status && data.agent_status.progress_pct > 0;
            
            if (isRestored) {
                connectionState.restored = true;
                connectionState.progress_pct = data.agent_status.progress_pct;
                
                // Display history ONLY if not already displayed
                if (!historyDisplayed && conversationHistory.length > 0) {
                    displayConversationHistory(conversationHistory);
                    historyDisplayed = true;
                }
                
                // Update form state
                handleReloadState(data.agent_status);
                
                showToast('🔄 Session restored (' + data.agent_status.progress_pct + '% complete)', 'info');
            } else {
                connectionState.restored = false;
                
                
                
                showToast('✨ New session started', 'info');
            }
            
            updateConnectionStatus();
        });
            
        


            socket.on('user_message', function(msg) {
               // Add to local history
                conversationHistory.push({
                    role: msg.role,
                    content: msg.content,
                    timestamp: msg.timestamp
                });
                
                // Display message
                addMessage(msg.role, msg.content, true);
            });

            
            socket.on('agent_message', function(data) {
                console.log('🤖 Agent message:', data);
                conversationHistory.push({
                role: 'assistant',
                content: data.message,
                timestamp: new Date().toISOString(),
                action: data.type
            });
                handleAgentMessage(data);
            });
            
            socket.on('conversation_reset', function(data) {
                console.log('🔄 Conversation reset:', data);
                
                // Clear local state
                conversationHistory = [];
                historyDisplayed = false;
                
                // Clear chat display
                const container = document.getElementById('chat-messages');
                if (container) container.innerHTML = '';
                
                showToast('🔄 Starting new conversation', 'info');
            });

            
            socket.on('error', function(data) {
                console.error('❌ Error:', data);
                addMessage('error', '❌ Error: ' + data.message);
                showToast('❌ Error: ' + data.message, 'error');
            });
            
            // ========================================
            // CONNECTION STATUS DISPLAY
            // ========================================
            
            function updateConnectionStatus() {
                const indicator = document.getElementById('connection-indicator');
                const status = document.getElementById('connection-status');
                const details = document.getElementById('connection-details');
                const sessionType = document.getElementById('session-type');
                
                if (!indicator || !status || !details) return;
                
                if (!connectionState.socket_connected) {
                    // Disconnected
                    indicator.style.color = '#f44336';
                    indicator.textContent = '●';
                    status.textContent = 'Disconnected';
                    details.textContent = 'Reconnecting...';
                } else if (!connectionState.agent_joined) {
                    // Connected but not joined
                    indicator.style.color = '#ff9800';
                    indicator.textContent = '●';
                    status.textContent = 'Connecting...';
                    details.textContent = 'Joining agent...';
                } else {
                    // Fully connected
                    indicator.style.color = '#4caf50';
                    indicator.textContent = '●';
                    status.textContent = 'Connected';
                    
                    if (connectionState.restored) {
                        details.textContent = '🔄 Session Restored';
                        if (sessionType) {
                            sessionType.textContent = 'Continuing previous conversation (' + connectionState.progress_pct + '% complete)';
                        }
                    } else {
                        details.textContent = '✨ New Session';
                        if (sessionType) {
                            sessionType.textContent = 'Fresh start -  Create your study ticket!';
                        }
                    }
                }
            }
            
            function updateConversationIdDisplay() {
                const display = document.getElementById('conversation-id-display');
                if (display) {
                    display.textContent = '🆔 Session: ' + conversationId;
                }
            }

            // ========================================
            // FORM PROGRESS
            // ========================================

            function renderForm(agentStatus) {
            const formContainer = document.getElementById('dynamic-form');
            if (!formContainer) return;

            formContainer.innerHTML = ''; // Clear existing form

            // Render filled fields
            const filledFields = agentStatus.filled_fields || {};
            for (const [key, value] of Object.entries(filledFields)) {
                const fieldDiv = document.createElement('div');
                fieldDiv.style.marginBottom = '10px';
                fieldDiv.innerHTML = `
                    <label style="font-weight:bold;">${key}:</label>
                    <input type="text" value="${value}" readonly style="width:100%; padding:8px; margin-top:2px; border:1px solid #ccc; border-radius:4px;" />
                `;
                formContainer.appendChild(fieldDiv);
            }

            // Render empty fields as editable inputs
            const emptyFields = agentStatus.empty_fields || [];
            emptyFields.forEach((field) => {
                const fieldDiv = document.createElement('div');
                fieldDiv.style.marginBottom = '10px';
                fieldDiv.innerHTML = `
                    <label style="font-weight:bold;">${field}:</label>
                    <input type="text" placeholder="Enter ${field}" style="width:100%; padding:8px; margin-top:2px; border:1px solid #ccc; border-radius:4px;" 
                    oninput="updateFieldValue('${field}', this.value)" />
                `;
                formContainer.appendChild(fieldDiv);
            });

            // Show quick actions if awaiting confirmation
            if (agentStatus.awaiting_confirmation) {
                showSuggestions(['yes', 'no']);
            }
        }
            function safeRenderForm(agentStatus) {
            const tryRender = () => {
                const formContainer = document.getElementById('dynamic-form');
                if (formContainer) {
                    renderForm(agentStatus);
                } else {
                    setTimeout(tryRender, 50); // Retry in 50ms
                }
            };
            tryRender();
        }

            let formValues = {};

            function updateFieldValue(field, value) {
                formValues[field] = value;
            }



            function handleReloadState(data) {
            updateProgress(data.progress_pct, data.filled_fields, data.empty_fields);

            // Update the dynamic form
            renderForm({
                filled_fields: data.filled_fields,
                empty_fields: data.empty_fields,
                awaiting_confirmation: data.awaiting_confirmation
            });

        }
            




            function handleAgentMessage(data) {
            // Update progress
            updateProgress(data.progress_pct, data.filled_fields, data.empty_fields);
            
            // Display message
            addMessage('agent', data.message, true);
            
            // Update form
            safeRenderForm({
                filled_fields: data.filled_fields,
                empty_fields: data.empty_fields,
                awaiting_confirmation: data.awaiting_confirmation
            });
            
            // Show suggestions if present
            if (data.suggestions && data.awaiting_confirmation) {
                showSuggestions(data.suggestions);
            }
        }



            // ========================================
            // TOAST NOTIFICATIONS
            // ========================================
            
            function showToast(message, type) {
                const toast = document.createElement('div');
                
                const colors = {
                    'success': '#4caf50',
                    'error': '#f44336',
                    'warning': '#ff9800',
                    'info': '#2196F3'
                };
                
                toast.style.cssText = `
                    padding: 15px 20px;
                    background: ${colors[type] || '#333'};
                    color: white;
                    borderRadius: 8px;
                    boxShadow: 0 4px 12px rgba(0,0,0,0.3);
                    marginBottom: 10px;
                    animation: slideInRight 0.3s ease-out;
                    maxWidth: 300px;
                `;
                toast.textContent = message;
                
                const container = document.getElementById('toast-container');
                if (container) {
                    container.appendChild(toast);
                    
                    setTimeout(() => {
                        toast.style.animation = 'slideOutRight 0.3s ease-in';
                        setTimeout(() => toast.remove(), 300);
                    }, 3000);
                }
            }

            
            // ========================================
            // DISPLAY CONVERSATION HISTORY (ONLY ON RESTORE)
            // ========================================


            function displayConversationHistory(history) {
                console.log('📜 Displaying conversation history:', history.length, 'messages');
                
                const container = document.getElementById('chat-messages');
                if (!container) return;
                
                // Clear existing messages
                container.innerHTML = '';
                
                // Add restoration banner
                if (history.length > 1) {  // More than just greeting
                    const banner = document.createElement('div');
                    banner.style.cssText = `
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: 10px 15px;
                        borderRadius: 8px;
                        textAlign: center;
                        fontSize: 13px;
                        marginBottom: 15px;
                        alignSelf: center;
                        maxWidth: 80%;
                        boxShadow: 0 2px 8px rgba(0,0,0,0.2);
                    `;
                    banner.innerHTML = `📜 <strong>Previous conversation restored</strong> (${history.length - 1} messages)`;
                    container.appendChild(banner);
                }
                
                // Display each historical message
                history.forEach(entry => {
                    addMessage(entry.role, entry.content, false);  // false = don't scroll yet
                });
                
                // Scroll to bottom after all messages loaded
                setTimeout(() => {
                    container.scrollTop = container.scrollHeight;
                }, 100);
            }
            
            // ========================================
            // MESSAGE DISPLAY
            // ========================================
            
            function addMessage(role, content) {
                const container = document.getElementById('chat-messages');
                if (!container) return;
                
                const messageDiv = document.createElement('div');
                messageDiv.className = 'message-enter';
                
                if (role === 'user') {
                    messageDiv.style.cssText = `
                        background: #667eea;
                        color: white;
                        padding: 12px 16px;
                        borderRadius: 18px 18px 4px 18px;
                        maxWidth: 70%;
                        alignSelf: flex-end;
                        marginLeft: auto;
                        wordWrap: break-word;
                        boxShadow: 0 2px 4px rgba(0,0,0,0.1);
                    `;
                } else if (role === 'assistant' || role === 'agent') {
                    messageDiv.style.cssText = `
                        background: white;
                        color: #333;
                        padding: 12px 16px;
                        borderRadius: 18px 18px 18px 4px;
                        maxWidth: 70%;
                        alignSelf: flex-start;
                        wordWrap: break-word;
                        boxShadow: 0 2px 4px rgba(0,0,0,0.1);
                        border: 1px solid #e0e0e0;
                    `;
                } else if (role === 'error') {
                    messageDiv.style.cssText = `
                        background: #ffebee;
                        color: #c62828;
                        padding: 12px 16px;
                        borderRadius: 8px;
                        border: 1px solid #ef5350;
                    `;
                }
                
                messageDiv.innerHTML = formatMessage(content);
                container.appendChild(messageDiv);
                container.scrollTop = container.scrollHeight;
            }
            
            function formatMessage(text) {
                return text
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/`(.*?)`/g, '<code style="background:#f5f5f5;padding:2px 4px;borderRadius:3px;">$1</code>')
                    .replace(/• (.*?)\\n/g, '• $1<br>')
                    .replace(/\\n\\n/g, '<br><br>')
                    .replace(/\\n/g, '<br>');
            }
      
            
            function updateProgress(percentage, filledFields, emptyFields) {
                connectionState.progress_pct = percentage;
                
                const percentEl = document.getElementById('progress-percentage');
                if (percentEl) percentEl.textContent = percentage + '%';
                
                const barEl = document.getElementById('progress-bar');
                if (barEl) barEl.style.width = percentage + '%';
                
                const filledCount = Object.keys(filledFields || {}).length;
                const emptyCount = emptyFields ? emptyFields.length : 0;
                
                const filledEl = document.getElementById('filled-fields-count');
                if (filledEl) {
                    filledEl.textContent = filledCount + ' field' + (filledCount !== 1 ? 's' : '') + ' filled';
                }
                
                const emptyEl = document.getElementById('empty-fields-count');
                if (emptyEl) {
                    emptyEl.textContent = emptyCount + ' field' + (emptyCount !== 1 ? 's' : '') + ' remaining';
                }
            }
            
            function showSuggestions(suggestions) {
                const actionsDiv = document.getElementById('quick-actions');
                if (!actionsDiv) return;
                
                actionsDiv.innerHTML = `
                    <div style="background: white; padding: 15px; borderRadius: 10px; boxShadow: 0 2px 8px rgba(0,0,0,0.1);">
                        <div style="fontSize: 14px; color: #666; marginBottom: 10px;">Quick actions:</div>
                        <div style="display: flex; gap: 10px;">
                            <button onclick="sendQuickMessage('yes')" style="
                                background: #4caf50; color: white; border: none;
                                padding: 10px 20px; borderRadius: 6px; cursor: pointer;
                                fontSize: 14px; fontWeight: bold;
                            ">✓ Accept</button>
                            <button onclick="sendQuickMessage('no')" style="
                                background: #f44336; color: white; border: none;
                                padding: 10px 20px; borderRadius: 6px; cursor: pointer;
                                fontSize: 14px; fontWeight: bold;
                            ">✗ Reject</button>
                        </div>
                    </div>
                `;
            }
            
            // ========================================
            // MESSAGE SENDING
            // ========================================
            
            window.sendMessage = function(message) {
                if (!message || !message.trim()) return;
                
                socket.emit('send_message', {
                    conversation_id: conversationId,
                    message: message.trim()
                });
                
                const actionsDiv = document.getElementById('quick-actions');
                if (actionsDiv) actionsDiv.innerHTML = '';
            };
            
            window.sendQuickMessage = function(message) {
                window.sendMessage(message);
            };
            
            // ========================================
            // NEW CONVERSATION
            // ========================================
            
            window.resetConversation = function() {
                const oldId = conversationId;
                
                // Tell server to clean up old session
                socket.emit('reset_conversation', {conversation_id: oldId});
                
                // Clear localStorage and generate new ID
                localStorage.removeItem('conversationId');
                conversationId = 'conv-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
                localStorage.setItem('conversationId', conversationId);
                
                console.log('🔄 Reset: ' + oldId + ' → ' + conversationId);
                
                // Reload page
                setTimeout(() => location.reload(), 500);
            };
            
            // ========================================
            // STATUS DISPLAY TOGGLE
            // ========================================
            
            window.toggleDebugInfo = function() {
                const display = document.getElementById('conversation-id-display');
                if (display) {
                    display.style.display = display.style.display === 'none' ? 'block' : 'none';
                }
                
                // Request status from server
                socket.emit('get_status', {conversation_id: conversationId});
            };
            
            socket.on('agent_status', function(status) {
                console.log('📊 Agent Status:', status);
                showToast('Status: ' + status.progress_pct + '% complete, ' + 
                         status.conversation_turns + ' turns', 'info');
            });
            
        </script>
    </body>
</html>
'''

# Callbacks
app.clientside_callback(
    """
    function(n_clicks, message) {
        if (n_clicks && message && message.trim()) {
            window.sendMessage(message);
            return '';
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output('message-input', 'value'),
    Input('send-btn', 'n_clicks'),
    State('message-input', 'value'),
    prevent_initial_call=True
)

app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks > 0) {
            window.resetConversation();
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output('new-conversation-btn', 'n_clicks'),
    Input('new-conversation-btn', 'n_clicks'),
    prevent_initial_call=True
)

app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks > 0) {
            window.toggleDebugInfo();
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output('show-status-btn', 'n_clicks'),
    Input('show-status-btn', 'n_clicks'),
    prevent_initial_call=True
)

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🤖 STUDYBOT ASSISTANT")
    print("="*60)
    print("📱 URL: http://localhost:8050")
    print("🔗 WebSocket: Enabled")
    print("🔄 Connection Reset: Enabled")
    print("="*60 + "\n")
    
    socketio.run(server, debug=True, host='127.0.0.1', port=8050, 
                 allow_unsafe_werkzeug=True, use_reloader=True)