import gevent.monkey
gevent.monkey.patch_all(aggressive=True)

import os

from core.application import Application

PKGDIR = os.path.dirname(__file__)
PKGNAME = os.path.basename(PKGDIR)
CONF = os.path.join(PKGDIR, '{}.ini'.format(PKGNAME))


def start(config, args):
    app = Application(config=config, args=args, root=PKGDIR)
    app.start()


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--conf', '-c', help='alternative configuration path',
                        default=CONF)
    args = parser.parse_args()
    start(args.conf, args)


if __name__ == '__main__':
    main()
