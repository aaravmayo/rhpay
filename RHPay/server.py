import socket
import threading
import csv
import time
import queue
import traceback

HOST = '127.0.0.1'
PORT = 5050
FORMAT = 'utf-8'
USER_FILE = 'users.csv'

users = {}
active_connections = {}  # Maps email to (connection, notification_queue) tuple


def load_users(csv_file='users.csv'):
    global users
    try:
        with open(csv_file, newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                users[row['email']] = {
                    'first_name': row['first_name'],
                    'last_name': row['last_name'],
                    'phone': row['phone'],
                    'password': row['password'],
                    'pin': row['pin'],
                    'balance': float(row['balance'])
                }
        print(f"[INFO] Loaded {len(users)} users from {csv_file}")
    except FileNotFoundError:
        print(f"[WARNING] User file {csv_file} not found. Starting with empty user database.")
    except Exception as e:
        print(f"[ERROR] Failed to load users: {e}")


def validate_user(email, password):
    if email in users and users[email]['password'] == password:
        return True
    return False


def save_users():
    try:
        with open(USER_FILE, 'w', newline='') as csvfile:
            # Get field names from the first user entry
            if not users:
                return

            fieldnames = ['email'] + list(next(iter(users.values())).keys())
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            # Convert the dictionary to the right format for writing
            for email, user_data in users.items():
                row = {'email': email}
                row.update(user_data)
                writer.writerow(row)
        print(f"[INFO] Saved {len(users)} users to {USER_FILE}")
    except Exception as e:
        print(f"[ERROR] Failed to save users: {e}")


def process_payment(sender_email, recipient_email, amount):
    if sender_email not in users:
        return False, f"Sender {sender_email} not found"

    if recipient_email not in users:
        return False, f"Recipient {recipient_email} not found"

    if users[sender_email]['balance'] < amount:
        return False, "Insufficient funds"

    # Process the transaction
    users[sender_email]['balance'] -= amount
    users[recipient_email]['balance'] += amount

    # Save the updated user data
    save_users()

    # Send notification to recipient if they're active
    send_notification(recipient_email, f"You received ${amount:.2f} from {sender_email}")

    return True, f"Successfully sent ${amount:.2f} to {recipient_email}"


def send_notification(user_email, message):
    """Send a notification to a user if they're active"""
    if user_email in active_connections:
        conn, _ = active_connections[user_email]
        try:
            notification = f"\n[NOTIFICATION] {message}\nEnter command (pay/request_money/balance/pending/exit):"
            conn.send(notification.encode(FORMAT))
            print(f"[NOTIFICATION] Sent to {user_email}: {message}")
        except Exception as e:
            print(f"[ERROR] Failed to send notification to {user_email}: {e}")


def request_money(requester_email, target_email, amount):
    """Send a money request to target user"""
    if target_email not in users:
        return False, f"User {target_email} not found"

    # Send notification to target if they're active
    if target_email in active_connections:
        send_notification(target_email, f"{requester_email} has requested ${amount:.2f} from you")
        return True, f"Request sent to {target_email} for ${amount:.2f}"
    else:
        # Store pending request for when the user logs in next time
        # (In a full implementation, this would be saved to a database)
        return True, f"Request sent to {target_email} for ${amount:.2f}"


def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")

    def send(msg):
        try:
            conn.send(msg.encode(FORMAT))
        except ConnectionAbortedError:
            print(f"[ERROR] Connection aborted by client {addr}")
            raise
        except Exception as e:
            print(f"[ERROR] Sending to {addr}: {e}")
            raise

    def recv():
        try:
            data = conn.recv(1024).decode(FORMAT).strip()
            print(f"[{addr} -> SERVER] Received: {data}")
            return data
        except Exception as e:
            print(f"[ERROR] Receiving from {addr}: {e}")
            return ""

    current_user = None

    try:
        send("LOGIN\nEnter Email:")
        email = recv()
        send("Enter Password:")
        password = recv()

        if not email or not password or not validate_user(email, password):
            send("Invalid credentials. Disconnecting.")
            return

        current_user = email

        # Register user as active
        active_connections[current_user] = (conn, queue.Queue())

        # Check for pending notifications (future enhancement)
        send(
            f"Login successful, {users[email]['first_name']}.\nYour balance: ${users[email]['balance']:.2f}\nEnter command (pay/request_money/balance/pending/exit):")

        while True:
            command = recv()
            if not command:
                print(f"[DISCONNECTED] {addr} disconnected.")
                break

            command = command.lower()

            if command == "pay":
                send("Enter recipient email:")
                recipient_email = recv()
                send("Enter amount:")
                amount_str = recv()

                try:
                    amount = float(amount_str)
                    if amount <= 0:
                        send("Amount must be positive. Try again.")
                    else:
                        success, msg = process_payment(current_user, recipient_email, amount)
                        send(msg)
                except ValueError:
                    send("Invalid amount. Please enter a number.")

                send(
                    f"Your balance: ${users[current_user]['balance']:.2f}\nEnter command (pay/request_money/balance/pending/exit):")

            elif command == "request_money":
                send("Enter sender email:")
                sender_email = recv()
                send("Enter amount:")
                amount_str = recv()

                try:
                    amount = float(amount_str)
                    if amount <= 0:
                        send("Amount must be positive.")
                    else:
                        success, msg = request_money(current_user, sender_email, amount)
                        send(msg)
                except ValueError:
                    send("Invalid amount. Please enter a number.")

                send("Enter command (pay/request_money/balance/pending/exit):")

            elif command == "balance":
                send(f"Your balance: ${users[current_user]['balance']:.2f}")
                send("Enter command (pay/request_money/balance/pending/exit):")

            elif command == "pending":
                # In a full implementation, this would check for pending requests in a database
                send("No pending requests at this time.")
                send("Enter command (pay/request_money/balance/pending/exit):")

            elif command == "exit":
                send("Goodbye!")
                break
            else:
                send("Unknown command. Try again.")
                send("Enter command (pay/request_money/balance/pending/exit):")

    except Exception as e:
        print(f"[ERROR] Exception for {addr}: {e}")
        traceback.print_exc()
        try:
            send("❌ Server error occurred.")
        except:
            pass
    finally:
        # Remove user from active connections
        if current_user and current_user in active_connections:
            del active_connections[current_user]
            print(f"[INFO] Removed {current_user} from active connections")

        conn.close()
        print(f"[DISCONNECTED] {addr} connection closed.")


def start():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[SERVER RUNNING] Listening on {HOST}:{PORT}")
    try:
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.daemon = True  # Makes threads exit when main program exits
            thread.start()
    except KeyboardInterrupt:
        print("[SERVER] Shutting down server...")
    finally:
        server.close()
        save_users()  # Save user data before exiting


if __name__ == "__main__":
    load_users()
    start()