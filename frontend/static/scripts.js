async function getUpdates(token, lastMessageId = 0) {
    const url = "/updates";
    const headers = new Headers({
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json"
    });

    const data = {
        last_message_id: lastMessageId
    };

    console.log(headers, data);

    try {
        const response = await fetch(url, {
            method: "POST",
            headers: headers,
            body: JSON.stringify(data)
        });

        if (response.ok) {
            const result = await response.json();
            console.log("Update response: ", result);
            return result;
        } else {
            console.error("Error fetching updates: ", response);
            return null;
        }
    } catch (error) {
        console.error("Error occurred: ", error);
        return null;
    }
}

function addMessage(messagesDiv, message = []) {
    const messageElement = document.createElement('div');
    messageElement.textContent = 'hello';
    messageElement.id = 0;

    if(message.length > 0) {
        messageElement.id = message[0];
        messageElement.classList.add('msg');
        const meOrNot = localStorage.getItem('username') === message[1] ? 'me' : 'not-me'
        messageElement.classList.add(meOrNot)
        messageElement.innerHTML = `<div><small>${message[4]}</small></div> <b>${message[1]}</b>: ${message[2]}`
    }

    messagesDiv.appendChild(messageElement);
}

// Wrapper function to request updates every second and update HTML
function startUpdates(token, lastMessageId = 0) {
    let messages = [];
    const chats = [];
    let doc_first = true;
    localStorage.setItem("last_message_id", 0);
    JSON.stringify(localStorage.setItem("messages", []));

    setInterval(async () => {
        const updates = await getUpdates(token, localStorage.getItem("last_message_id"));
        if (updates && updates.new_messages) {
            if (localStorage.getItem("role") == "Doctor") {
                const messagesDiv = document.getElementById('messages');
                document.getElementById('room').classList.remove('hidden');
                const dropdown = document.getElementById("room");
                messages = messages.concat(updates.new_messages);
                messages.forEach(message => {
                    if (chats.indexOf(message[1]) == -1) {
                        chats.push(message[1]);
                        var opt = document.createElement('option');
                        opt.value = message[1];
                        opt.innerHTML = message[1];
                        dropdown.appendChild(opt);
                    }
                });

                const cur_chat = document.getElementById("room").value;
                localStorage.setItem('current_chat', cur_chat);
                if (cur_chat != "Select room") {
                    let messages_to_show = [];
                    messagesDiv.innerHTML = "";
                    messages.forEach(message => {
                        if (message[1] == cur_chat) {
                            addMessage(messagesDiv, message);
                        }
                    });
                } else {
                    doc_first = true;
                }
            }
            else {
                const messagesDiv = document.getElementById('messages');
                updates.new_messages.forEach(message => {
                    addMessage(messagesDiv, message);
                });
            }

            if (updates.new_messages.length > 0) {
                lastMessageId = updates.new_messages[updates.new_messages.length - 1].id;
            }
            const lmid = parseInt(localStorage.getItem("last_message_id"), 10);
            localStorage.setItem("last_message_id", lmid + updates.new_messages.length);
        }
    }, 1000);
}

async function sendMessage(messageText, recipient = null) {
    const token = localStorage.getItem("AuthToken");

    const requestBody = {
        message_text: messageText,
        recipient: recipient
    };

    try {
        const response = await fetch("/send_message", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            throw new Error("Network response was not ok");
        }

        const result = await response.json();
        return result;

    } catch (error) {
        console.error("Error sending message:", error);
        return false;
    }
}