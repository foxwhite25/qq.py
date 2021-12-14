from setuptools import setup

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

with open('README.md', encoding='utf-8') as f:
    readme = f.read()

extras_require = {
    'docs': [
        'sphinx==4.0.2',
        'sphinxcontrib_trio==1.1.2',
        'sphinxcontrib-websupport',
    ],
}

setup(
    name='qq.py',
    version='1.0.3',
    description='QQ 频道 API 的 Python Wrapper',
    py_modules=["qq"],
    packages=['qq', "qq.types", "qq.ext.commands", "qq.ext.tasks"],
    license='MIT',
    long_description=readme,
    long_description_content_type="text/markdown",
    install_requires=requirements,
    extras_require=extras_require,
    python_requires='>=3.8.0',
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Natural Language :: Chinese (Simplified)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Internet',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities',
        'Typing :: Typed',
    ],
    url="https://github.com/foxwhite25/qq.py",
    author='foxwhite25',
    author_email='vct.xie@gmail.com'
)
