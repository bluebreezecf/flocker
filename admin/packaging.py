# Copyright Hybrid Logic Ltd.  See LICENSE file for details.

"""
Helper utilities for the Flocker packaging
"""

from subprocess import check_call
from tempfile import mkdtemp

from twisted.python.filepath import FilePath
from characteristic import attributes
import virtualenv

from .release import make_rpm_version

@attributes(['steps'])
class BuildSequence(object):
    """
    Run the supplied `steps` in consecutively.
    """
    def run(self):
        for step in self.steps:
            step.run()


@attributes(['target_path'])
class InstallVirtualEnv(object):
    """
    Install a virtualenv in the supplied `target_path`.
    """
    def run(self):
        virtualenv.create_environment(
            self.target_path.path,
            site_packages=False,
            clear=False,
            unzip_setuptools=False,
            prompt=None,
            search_dirs=None,
            never_download=False,
            no_setuptools=False,
            no_pip=False,
            symlink=True
        )


@attributes(['virtualenv_path', 'package_path'])
class InstallApplication(object):
    """
    Install the supplied `package_path` using `pip` from the supplied
    `virtualenv_path`.
    """
    def run(self):
        pip_path = self.virtualenv_path.child('bin').child('pip').path
        check_call(
            [pip_path, '--quiet', 'install', self.package_path.path]
        )


@attributes(['source_path', 'name', 'rpm_version', 'license', 'url'])
class BuildRpm(object):
    """
    Use `fpm` to build an RPM file from the supplied `source_path`.
    """
    def run(self):
        """
        """
        check_call([
            'fpm',
            '-s', 'dir',
            '-t', 'rpm',
            '--name', self.name,
            '--version', self.rpm_version.version,
            '--iteration', self.rpm_version.release,
            '--license', self.license,
            '--url', self.url,
            self.source_path.path]
        )


def sumo_rpm_builder(package_path, version, target_dir=None):
    """
    Build an RPM file containing the supplied `package` and all its
    dependencies.

    Motivation:
    * We depend on libraries which are not packaged for the target OS.
    * We depend on newer versions of libraries which have not yet been included in the target OS.

    Disadvantages:
    * We won't be able to take advantage of library security updates shipped by the target OS.
      * But by shipping our own separate dependency packages we will need to be responsible for shipping security patches in those packages.
      * And rather than being responsible only for the security of Flocker, we become responsible for the security of all other packages that depend on that package.
    * Packages will be larger.

    Plan:
    * Create a temporary working dir.
    * Create virtualenv with `--system-site-packages`
      * Allows certain python libraries to be supplied by the operating system.
    * Install flocker from wheel file (which will include all the dependencies).
      * We'll need to keep track of which of our dependencies are provided on each platform and somehow omit those for from the build for that platform.
    * Generate an RPM version number.
    * Run `fpm` supplying the virtualenv path and version number.


    Followup Issues:
    * Update all pinned dependencies to instead be minimum dependencies.
      * This means that as and when sufficiently new versions of our dependencies are introduced upstream, we can remove them from our sumo build.
      * Those dependencies which are either too old or which are not packaged will be imported from the sumo virtualenv in preference.
      * Eventually we hope that all our dependencies will filter upstream and we will no longer have to bundle them; at which point the `flocker` package itself may be ready to be packaged by upstream distributions.

    Ticket refs:
         * https://github.com/ClusterHQ/flocker/issues/88

    Issue: CI integration (??):
    Update buildbot to build RPMs using new build scripts
    * Issue: create deb, mac, gentoo build slave
    * Issue: install from resulting package from repo and run test suite

    Issue: Client package build (??):
    Sumo packaging of flocker-deploy
    * For deb, RPM, and mac (via homebrew or ...)
    * Proper mac packages. See http://stackoverflow.com/questions/11487596/making-os-x-installer-packages-like-a-pro-xcode4-developer-id-mountain-lion-re

    Client package CI integration

    Misc:
    * separate stable and testing repos for deb and rpm
    * update python-flocker.spec.in requirements (remove most of them)
    * maybe even remove the spec file template and generate_spec function entirely (do we need it?)
    * do we still need to build an SRPM?
    * automatically build a wheel
    * automatically build an sdist
    """
    if target_dir is None:
        target_dir = FilePath(mkdtemp())
    return BuildSequence(
        steps=(
            InstallVirtualEnv(target_path=target_dir),
            InstallApplication(virtualenv_path=target_dir, 
                               package_path=package_path),
            BuildRpm(
                source_path=target_dir,
                name='Flocker',
                rpm_version=make_rpm_version(version),
                license='ASL 2.0',
                url='https://clusterhq.com',
            )
        )
    )
