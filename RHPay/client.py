import socket


def interact(client, FORMAT='utf-8'):
    def send(msg):
        print(f"[CLIENT -> SERVER] Sending: {msg}")
        client.send(msg.encode(FORMAT))

    def recv():
        try:
            data = client.recv(1024).decode(FORMAT)
            print(f"[SERVER -> CLIENT] Received: {data}")
            return data
        except Exception as e:
            print(f"Connection error: {e}")
            return None

    try:
        # Initial connection - expect login prompts
        while True:
            response = recv()
            if not response:
                print("❌ Server closed connection")
                break

            # Check for notifications
            if "[NOTIFICATION]" in response:
                # Print the notification clearly
                notification_parts = response.split("[NOTIFICATION]")
                print("\n" + "=" * 50)
                print("NOTIFICATION: " + notification_parts[1].split("\nEnter command")[0].strip())
                print("=" * 50 + "\n")

                # Extract the command prompt part
                cmd_prompt = notification_parts[1].split("\nEnter command")[1].strip()
                print(f"Enter command ({cmd_prompt}):")
                command = input("> ")
                send(command)
                continue

            # Handle login flow
            if "Enter Email:" in response:
                email = input("Email: ")
                send(email)
            elif "Enter Password:" in response:
                password = input("Password: ")
                send(password)
            elif "Invalid credentials" in response:
                print("Login failed!")
                break
            # Handle command prompts
            elif "Enter command" in response:
                # Extract available commands
                available_commands = response.split("Enter command (")[1].split("):")[0]
                print(f"\nAvailable commands: {available_commands}")
                command = input("> ")
                send(command)
            # Handle payment flow
            elif "Enter recipient email:" in response:
                recipient = input("Recipient email: ")
                send(recipient)
            elif "Enter amount:" in response:
                amount = input("Amount: ")
                send(amount)
            elif "Enter sender email:" in response:
                sender = input("Sender email: ")
                send(sender)
            # Exit condition
            elif "Goodbye!" in response:
                print("Session ended.")
                break
            # For any other server message, just show it and wait for the next one
            else:
                continue

    except Exception as e:
        print(f"❌ Client error: {e}")
    finally:
        client.close()
        print("Connection closed.")


def main():
    HOST = '127.0.0.1'
    PORT = 5050
    FORMAT = 'utf-8'

    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f"Connecting to {HOST}:{PORT}...")
        client.connect((HOST, PORT))
        print("Connected! Starting session...")
        interact(client, FORMAT)
    except ConnectionRefusedError:
        print("❌ Connection refused. Is the server running?")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()