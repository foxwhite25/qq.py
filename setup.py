from setuptools import setup

with open('README.md', encoding='utf-8') as f:
    readme = f.read()

setup(
    name='qq.py',
    version='0.1.2',
    description='A Python wrapper for the QQ Channel API',
    py_modules=["qq"],
    packages=['qq', "qq.types"],
    license='MIT',
    long_description=readme,
    long_description_content_type="text/markdown",
    python_requires='>=3.8.0',
    classifiers=[
        'Development Status :: 3 - Alpha',
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
