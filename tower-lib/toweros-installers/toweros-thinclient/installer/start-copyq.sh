copyq &
cat <<EOF | copyq eval -
var cmds = commands()
var command_added = false
for (var i = 0; i < cmds.length; i++) {
    if (cmds[i].name == 'Enable copy/past from host to host') {
        command_added = true
        break
    }
}
if (!command_added) {
    cmds.unshift({
        name: 'Enable copy/past from host to host',
        automatic: true,
        input: 'text/plain',
        cmd: 'copyq: copy(clipboard())'
    })
    setCommands(cmds)
}
EOF
