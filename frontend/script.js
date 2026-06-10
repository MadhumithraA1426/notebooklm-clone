async function uploadFile() {

    const file =
    document.getElementById(
        "fileInput"
    ).files[0];

    const formData =
    new FormData();

    formData.append(
        "file",
        file
    );

    const response =
    await fetch(
        "http://127.0.0.1:8000/upload",
        {
            method: "POST",
            body: formData
        }
    );

    const data =
    await response.json();

    document.getElementById(
        "result"
    ).innerText =
    JSON.stringify(
        data,
        null,
        2
    );
}