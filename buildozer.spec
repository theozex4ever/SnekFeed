[app]
title = Snek Feed
package.name = snekfeed
package.domain = io.github.theozex4ever

source.dir = .
source.include_exts = py
source.exclude_dirs = tests, docs, tools, assets, bin, .github, .buildozer
source.exclude_patterns = *__pycache__*

version.regex = __version__ = ['"](.*)['"]
version.filename = %(source.dir)s/snekfeed/__init__.py

requirements = python3,pygame

icon.filename = %(source.dir)s/assets/icon.png
presplash.filename = %(source.dir)s/assets/presplash.png
android.presplash_color = #FFF6EC

orientation = landscape, landscape-reverse
android.manifest.orientation = sensorLandscape
fullscreen = 1
# API 36 stops delivering the back key to SDL unless predictive back is turned off.
android.extra_manifest_application_arguments = %(source.dir)s/tools/android/manifest_application_arguments.xml

android.api = 36
android.minapi = 24
android.ndk = 28c
android.archs = arm64-v8a, armeabi-v7a

# CI sets APP_ANDROID_ACCEPT_SDK_LICENSE=True; locally you get the license prompt.
android.accept_sdk_license = False
android.logcat_filters = *:S python:D

p4a.branch = master
p4a.bootstrap = sdl2
# pygame recipe bumped to 2.6.1, see tools/p4a-recipes/pygame
p4a.local_recipes = %(source.dir)s/tools/p4a-recipes

[buildozer]
log_level = 2
warn_on_root = 1
