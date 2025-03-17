// Fetch To Do tasks from DB
fetch("/api/task")
    .then((response) => response.json())
    .then((data) => {
        console.log(data);
        for (let i = 0; i < data.length; i++) {
            let li = document.createElement("li");
            li.innerHTML =
                "<input type='checkbox'>" + data[i][1] + "<button class='delete'>DELETE</button>";
            li.setAttribute("id", data[i][0]);
            if (data[i][2] === 1) {
                li.style.textDecoration = "line-through";
                li.childNodes[0].checked = true;
                li.childNodes[2].style.textDecoration = "none";
            }
            document.getElementById("taskList").appendChild(li);
        }
    })
    .catch((err) => {
        window.location.reload();
        console.log("Task Fetching error: ", err);
    });

// Update Task in DB and UI
function updateTask(id) {
    const url = `/api/task/${id}`;
    fetch(url, { method: "PATCH" })
        .then(() => {
            const checkedElement = document.getElementById(`${id}`);
            const checkedBox = checkedElement.childNodes[0].checked;
            if (checkedBox) {
                checkedElement.style.textDecoration = "line-through";
            } else {
                checkedElement.style.textDecoration = "None";
            }
        })
        .catch((err) => console.log("Task Update Error: ", err));
}

// Delete Task in DB and UI
function deleteTask(id) {
    const url = `/api/task/${id}`;
    fetch(url, { method: "DELETE" }).then(() => {
        const checkedElement = document.getElementById(`${id}`);
        checkedElement.parentNode.removeChild(checkedElement);
    });
}

// function Log Out
function logOut() {
    fetch("/api/logout");
    window.location.reload();
}

// Event Listener on Checkbox and Delete button
document.addEventListener("DOMContentLoaded", () => {
    document.body.addEventListener("click", (event) => {
        if (event.target && event.target.type === "checkbox") {
            const id = event.target.parentNode.getAttribute("id");
            updateTask(id);
        } else if (
            event.target &&
            event.target.tagName === "BUTTON" &&
            event.target.classList.contains("delete")
        ) {
            const id = event.target.parentNode.getAttribute("id");
            deleteTask(id);
        } else if (event.target && event.target.tagName === "H2") {
            logOut();
        }
    });
});
