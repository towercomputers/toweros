import os
import logging
import re

from towerlib import sshconf
from towerlib import gui, vnc
from towerlib.utils.exceptions import TowerException

logger = logging.getLogger('tower')

def add_args(argparser):
    help_message = "Run an application on the specified host, with the GUI on the thin client."
    run_parser = argparser.add_parser(
        'run',
        help=help_message, description=help_message
    )
    run_parser.add_argument(
        'host',
        help="""Host's name. This name must match the `name` used with the `provision` command. (Required)""",
        nargs=1
    )
    run_parser.add_argument(
        'run_command',
        help="""Command to execute on the host with NX protocol. (Required)""",
        nargs='+'
    )
    run_parser.add_argument(
        '--uncolored',
        help="""Don't use host color for window headerbar. (Default: False)""",
        required=False,
        action='store_true',
        default=False
    )
    run_parser.add_argument(
        '--nx',
        help="""Use `nx` instead `vnc`. (Default: False)""",
        required=False,
        action='store_true',
        default=False
    )
    run_parser.add_argument(
        '--nx-link',
        help="""The value can be either 'modem', 'isdn', 'adsl', 'wan', 'lan', 'local' or a bandwidth specification, like for example '56k', '1m', '100m'""",
        required=False,
        default="adsl"
    )
    run_parser.add_argument(
        '--nx-limit',
        help="""Specify a bitrate limit allowed for this session. (Default: 0)""",
        type=int,
        required=False,
        default=0
    )
    run_parser.add_argument(
        '--nx-images',
        help="""Size of the persistent image cache. (Default: 512M)""",
        required=False,
        default="512M"
    )
    run_parser.add_argument(
        '--nx-cache',
        help="""Size of the in-memory X message cache. Setting the value to 0 will disable the memory cache as well as the NX differential compression. (Default: 1G)""",
        required=False,
        default="1G"
    )
    run_parser.add_argument(
        '--nx-stream',
        help="""Enable or disable the ZLIB stream compression. The value must be between 0 and 9.""",
        choices=range(10),
        type=int,
        required=False
    )
    run_parser.add_argument(
        '--nx-data',
        help="""Enable or disable the ZLIB stream compression. The value must be between 0 and 9.""",
        choices=range(10),
        type=int,
        required=False
    )
    run_parser.add_argument(
        '--nx-delta',
        help="""Enable X differential compression.""",
        choices=['0', '1'],
        required=False
    )
    run_parser.add_argument(
        '--waypipe',
        help="""Use `waypipe` instead `vnc`. (Default: False)""",
        required=False,
        action='store_true',
        default=False
    )
    run_parser.add_argument(
        '--wp-compress',
        help="""Select the compression method applied to data transfers. Options are none (for high-bandwidth networks), lz4 (intermediate), zstd (slow connection). The default compression is none. The compression level can be chosen by appending = followed by a number. For example, if C is zstd=7, waypipe will use level 7 Zstd compression.""",
        required=False,
    )
    run_parser.add_argument(
        '--wp-threads',
        help="""Set the number of total threads (including the main thread) which a waypipe instance will create. These threads will be used to parallelize compression operations. This flag is passed on to waypipe server when given to waypipe ssh. The flag also controls the thread count for waypipe bench. The default behavior (choosable by setting T to 0) is to use half as many threads as the computer has hardware threads available.""",
        type=int,
        required=False
    )
    run_parser.add_argument(
        '--wp-video',
        help="""Compress specific DMABUF formats using a lossy video codec. Opaque, 10-bit, and multiplanar formats, among others, are not supported. V is a comma separated list of options to control the video encoding. Using the --video flag without setting any options is equivalent to using the default setting of: --video=sw,bpf=120000,h264. Later options supersede earlier ones (see `man waypipe` for more options).""",
        required=False
    )


def check_nx_args(args, parser_error):
    links = ['modem', 'isdn', 'adsl', 'wan', 'lan', 'local']
    regex = r'^[0-9]+[kmgKMG]{1}$'
    if args.nx_link and not re.match(regex, args.nx_link) and args.nx_link not in links:
        parser_error("Invalid link name")
    if args.nx_images and not re.match(regex, args.nx_images) and not args.nx_images.isdigit():
        parser_error("Invalid images size")
    if args.nx_cache and not re.match(regex, args.nx_cache) and not args.nx_cache.isdigit():
        parser_error("Invalid cache size")

def check_waypipe_args(args, parser_error):
    if args.wp_compress:
        compressions = ['none', 'lz4', 'zstd']
        regex = r'^(lz4|zstd)=[0-9]{1}$'
        if not re.match(regex, args.wp_compress) and args.wp_compress not in compressions:
            parser_error("Invalid compression method")
    if args.wp_video:
        options = args.wp_video.split(',')
        regex_bpf = r'^bpf=[0-9]{1,6}$'
        for option in options:
            if not re.match(regex_bpf, option) and option not in ['sw', 'hw', 'h264', 'vp9']:
                parser_error("Invalid video option")

def check_args(args, parser_error):
    config = sshconf.get(args.host[0])
    if config is None:
        parser_error("Unknown host.")
    if args.waypipe:
        check_waypipe_args(args, parser_error)
    else:
        check_nx_args(args, parser_error)

def execute(args):
    if os.getenv('DISPLAY'):
        if args.nx:
            nxagent_args = {
                "link": args.nx_link,
                "limit": args.nx_limit,
                "images": args.nx_images,
                "cache": args.nx_cache,
            }
            if args.nx_stream:
                nxagent_args["stream"] = args.nx_stream
            if args.nx_data:
                nxagent_args["data"] = args.nx_data
            if args.nx_delta:
                nxagent_args["delta"] = args.nx_delta
            gui.run(args.host[0], nxagent_args, *args.run_command)
        elif args.waypipe:
            waypipe_args = []
            if args.wp_compress:
                waypipe_args += ["--compress", args.wp_compress]
            if args.wp_threads:
                waypipe_args += ["--threads", args.wp_threads]
            if args.wp_video:
                waypipe_args += ["--video", args.wp_video]
            gui.run_waypipe(args.host[0], waypipe_args, *args.run_command)
        else:
            vnc.run(args.host[0], ' '.join(args.run_command), args.uncolored)
    else:
        raise TowerException("`tower run` requires a running desktop environment. Use `startw` to start Labwc.")
