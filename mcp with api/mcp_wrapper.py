import sys
import subprocess
import threading

# Path to the actual MCP server
# SERVER_COMMAND = ["node", "E:\\Adaptive-Personal-Risk-Intelligence-MCP-Server\\dist\\server.js"]
SERVER_COMMAND = ["E:\\Sem-6\\Fintech-Project\\mcp with api\\MCP-Server\\.venv\\Scripts\\python.exe", "E:\\Sem-6\\Fintech-Project\\mcp with api\\MCP-Server\\main.py"]

def forward_stdin(process):
    try:
        while True:
            # Read from our stdin (binary)
            data = sys.stdin.buffer.read1(1024)
            if not data:
                break
            # Write to server's stdin
            process.stdin.write(data)
            process.stdin.flush()
    except Exception as e:
        try:
            sys.stderr.write(f"Error forwarding stdin: {e}\n")
        except:
            pass
    finally:
        try:
            process.stdin.close()
        except:
            pass

def process_stdout(process):
    try:
        # Read server's stdout line by line
        for line in iter(process.stdout.readline, b''):
            try:
                # Try to decode line to check if it's JSON
                text = line.decode('utf-8').strip()
                if not text:
                    continue
                
                # Check for JSON start
                if text.startswith('{'):
                    # It's likely a JSON-RPC message, verify valid JSON (optional but safer)
                    # json.loads(text) # This might be too slow, header check is usually enough
                    
                    # Write to our stdout (binary)
                    sys.stdout.buffer.write(line)
                    sys.stdout.buffer.flush()
                else:
                    # Log extraneous output to stderr so it doesn't break the protocol
                    try:
                        sys.stderr.write(f"[MCP-SERVER-LOG]: {text}\n")
                        sys.stderr.flush()
                    except:
                        pass
            except Exception:
                # If decoding fails or other issues, just dump it to stderr to be safe
                try:
                    sys.stderr.write(f"[MCP-SERVER-RAW]: {line}\n")
                except:
                    pass
    except Exception as e:
        try:
            sys.stderr.write(f"Error processing stdout: {e}\n")
        except:
            pass
    finally:
        try:
            process.stdout.close()
        except:
            pass

def main():
    # Start the server process
    # stderr=sys.stderr means server's stderr goes directly to our stderr, which is fine
    try:
        process = subprocess.Popen(
            SERVER_COMMAND,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr
        )
    except Exception as e:
        try:
            sys.stderr.write(f"Failed to start server process: {e}\n")
        except:
            pass
        return

    t_stdin = threading.Thread(target=forward_stdin, args=(process,))
    t_stdout = threading.Thread(target=process_stdout, args=(process,))

    t_stdin.daemon = True
    t_stdout.daemon = True

    t_stdin.start()
    t_stdout.start()

    return_code = process.wait()
    sys.exit(return_code)

if __name__ == "__main__":
    main()
