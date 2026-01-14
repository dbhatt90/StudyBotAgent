"""
Websocket.py - Enhanced WebSocket handler with better error handling and logging
"""

from flask_socketio import SocketIO, emit, join_room, leave_room
import asyncio
from core import StudyBotAgent
import os
from dotenv import load_dotenv
from flask import request
from datetime import datetime
import traceback

load_dotenv()

# Global storage for active agents
active_agents = {}

def init_socketio(app):
    """Initialize SocketIO with StudyBot integration"""
    
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode='threading',
        logger=True,
        engineio_logger=True,  # Enable for debugging
        ping_timeout=60,
        ping_interval=25
    )
    
    @socketio.on('connect')
    def handle_connect():
        print(f'\n{"="*60}')
        print(f'✅ CLIENT CONNECTED')
        print(f'   Socket ID: {request.sid}')
        print(f'   Remote: {request.remote_addr}')
        print(f'{"="*60}\n')
        
        try:
            emit('connection_established', {'status': 'connected', 'socket_id': request.sid})
        except Exception as e:
            print(f'❌ Error sending connection_established: {e}')
    
    @socketio.on('disconnect')
    def handle_disconnect():
        print(f'\n{"="*60}')
        print(f'❌ CLIENT DISCONNECTED')
        print(f'   Socket ID: {request.sid}')
        print(f'{"="*60}\n')
    
    @socketio.on('join_conversation')
    def handle_join(data):
        """
        Handle joining conversation - sends history ONLY here
        """
        try:
            conversation_id = data.get('conversation_id')
            
            print(f'\n{"="*60}')
            print(f'📥 JOIN CONVERSATION REQUEST')
            print(f'   Conversation ID: {conversation_id}')
            print(f'   Socket ID: {request.sid}')
            print(f'{"="*60}')
            
            if not conversation_id:
                print('❌ No conversation_id provided')
                emit('error', {'message': 'No conversation_id provided'})
                return
            
            # Join the room
            join_room(conversation_id)
            print(f'✅ Joined room: {conversation_id}')
            
            # Track if this is a NEW agent or EXISTING (restored)
            is_new_session = conversation_id not in active_agents
            
            # Create or get agent
            if is_new_session:
                print(f'🆕 Creating new agent for: {conversation_id}')
                
                def websocket_callback(session_id, message_dict):
                    """
                    Callback for regular messages - NO history included
                    """
                    try:
                        # Remove conversation_history if present (optimization)
                        if 'conversation_history' in message_dict:
                            del message_dict['conversation_history']
                        
                        print(f'📤 Sending message to room {session_id}')
                        socketio.emit('agent_message', message_dict, room=session_id)
                    except Exception as e:
                        print(f'❌ Error in websocket_callback: {e}')
                        traceback.print_exc()
                
                try:
                    agent = StudyBotAgent(
                        session_id=conversation_id,
                        api_key=os.getenv('GOOGLE_API_KEY'),
                        rag_client=None,
                        websocket_callback=websocket_callback
                    )
                    
                    active_agents[conversation_id] = agent
                    print(f'✅ Agent created successfully')
                    
                except Exception as e:
                    print(f'❌ Error creating agent: {e}')
                    traceback.print_exc()
                    emit('error', {'message': f'Failed to create agent: {str(e)}'})
                    return
            else:
                print(f'♻️ Reusing existing agent for: {conversation_id}')
            
            # Get agent
            agent = active_agents[conversation_id]
            
            # Get status with history
            agent_status = agent.get_status()
            conversation_history = agent.session.get("conversation_history", [])
            
            print(f'📊 Agent Status:')
            print(f'   Progress: {agent_status.get("progress_pct", 0)}%')
            print(f'   Turns: {agent_status.get("conversation_turns", 0)}')
            print(f'   History messages: {len(conversation_history)}')
            print(f'   Filled: {len(agent_status.get("filled_fields", {}))}')
            print(f'   Empty: {len(agent_status.get("empty_fields", []))}')
            
            # Send confirmation with history (ONLY on join)
            response = {
                'conversation_id': conversation_id,
                'status': 'joined',
                'is_new_session': is_new_session,
                'agent_status': agent_status,
                'conversation_history': conversation_history  # ← ONLY sent here
            }
            
            emit('joined_conversation', response)
            print(f'✅ Sent joined_conversation with {len(conversation_history)} messages')
            print(f'{"="*60}\n')
            
        except Exception as e:
            print(f'❌ Error in handle_join: {e}')
            traceback.print_exc()
            emit('error', {'message': f'Join failed: {str(e)}'})
    
    
    @socketio.on('send_message')
    def handle_message(data):
        try:
            conversation_id = data.get('conversation_id')
            message = data.get('message', '').strip()
            
            print(f'\n{"="*60}')
            print(f'📨 MESSAGE RECEIVED')
            print(f'   Conversation: {conversation_id}')
            print(f'   Socket ID: {request.sid}')
            print(f'   Message: {message[:100]}{"..." if len(message) > 100 else ""}')
            print(f'{"="*60}')
            
            if not conversation_id or not message:
                print('❌ Invalid message data')
                emit('error', {'message': 'Invalid message data'})
                return
            
            if conversation_id not in active_agents:
                print(f'❌ Agent not found for: {conversation_id}')
                print(f'   Active agents: {list(active_agents.keys())}')
                emit('error', {'message': 'Agent not found. Join conversation first.'})
                return
            
            agent = active_agents[conversation_id]
            print(f'✅ Agent found, processing message...')
            
            # Echo user message
            socketio.emit('user_message', {
                'role': 'user',
                'content': message,
                'timestamp': datetime.now().isoformat()
            }, room=conversation_id)
            
            # Process message in background
            def process_message():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    print(f'⚙️ Processing message in agent...')
                    response = loop.run_until_complete(agent.handle_message(message))
                    print(f'✅ Agent response completed')
                    print(f'   Response type: {type(response)}')
                    
                except Exception as e:
                    print(f'❌ Error processing message: {e}')
                    traceback.print_exc()
                    socketio.emit('error', {
                        'message': f'Error: {str(e)}'
                    }, room=conversation_id)
                finally:
                    loop.close()
            
            socketio.start_background_task(process_message)
            print(f'🚀 Background task started')
            print(f'{"="*60}\n')
            
        except Exception as e:
            print(f'❌ Error in handle_message: {e}')
            traceback.print_exc()
            emit('error', {'message': f'Message handling failed: {str(e)}'})
    
    @socketio.on('get_status')
    def handle_get_status(data):
        try:
            conversation_id = data.get('conversation_id')
            
            print(f'\n📊 STATUS REQUEST: {conversation_id}')
            
            if conversation_id and conversation_id in active_agents:
                agent = active_agents[conversation_id]
                status = agent.get_status()
                emit('agent_status', status)
                print(f'✅ Status sent')
            else:
                print(f'❌ Agent not found')
                emit('error', {'message': 'Agent not found'})
                
        except Exception as e:
            print(f'❌ Error in handle_get_status: {e}')
            traceback.print_exc()
            emit('error', {'message': f'Status request failed: {str(e)}'})
    
    @socketio.on('reset_conversation')
    def handle_reset(data):
        try:
            conversation_id = data.get('conversation_id')
            
            print(f'\n{"="*60}')
            print(f'🔄 RESET CONVERSATION: {conversation_id}')
            print(f'{"="*60}')
            
            if conversation_id and conversation_id in active_agents:
                agent = active_agents[conversation_id]
                
                # Delete checkpoint
                try:
                    agent.checkpoint_mgr.delete(conversation_id)
                    print(f'✅ Checkpoint deleted')
                except Exception as e:
                    print(f'⚠️ Error deleting checkpoint: {e}')
                
                # Create new agent
                def websocket_callback(session_id, message_dict):
                    try:
                        socketio.emit('agent_message', message_dict, room=session_id)
                    except Exception as e:
                        print(f'❌ Error in websocket_callback: {e}')
                
                agent = StudyBotAgent(
                    session_id=conversation_id,
                    api_key=os.getenv('GOOGLE_API_KEY'),
                    rag_client=None,
                    websocket_callback=websocket_callback
                )
                
                active_agents[conversation_id] = agent
                
                emit('conversation_reset', {
                    'status': 'reset',
                    'conversation_id': conversation_id
                })
                
                print(f'✅ Conversation reset complete')
                print(f'{"="*60}\n')
            else:
                print(f'❌ Agent not found')
                emit('error', {'message': 'Agent not found'})
                
        except Exception as e:
            print(f'❌ Error in handle_reset: {e}')
            traceback.print_exc()
            emit('error', {'message': f'Reset failed: {str(e)}'})
    
    print('\n' + '='*60)
    print('✅ SocketIO initialized with handlers:')
    print('   - connect')
    print('   - disconnect')
    print('   - join_conversation')
    print('   - send_message')
    print('   - get_status')
    print('   - reset_conversation')
    print('='*60 + '\n')
    
    return socketio