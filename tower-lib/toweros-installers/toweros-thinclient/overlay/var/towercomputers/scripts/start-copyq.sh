QT_QPA_PLATFORM=xcb copyq &
cat <<EOF | copyq eval -
var cmds = commands()
var command_added = false
for (var i = 0; i < cmds.length; i++) {
    if (cmds[i].name == 'Enable copy/paste between hosts') {
        command_added = true
        break
    }
}
if (!command_added) {
    cmds.unshift({
        name: 'Enable copy/paste between hosts',
        automatic: true,
        input: 'text/plain',
        cmd: 'copyq: copy(clipboard())'
    })
    setCommands(cmds)
}
EOF
