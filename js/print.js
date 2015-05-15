function page_print() {
    var element = document.getElementById("toolbarhide");
    if (!isNull(element)) {
        element.style.display = "none";
    }
    if (window.print) {
        window.print();
    }
    if (!isNull(element)) {
        element.style.display = "block";
    }
}
