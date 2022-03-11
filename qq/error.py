#  The MIT License (MIT)
#  Copyright (c) 2021-present foxwhite25
#
#  Permission is hereby granted, free of charge, to any person obtaining a
#  copy of this software and associated documentation files (the "Software"),
#  to deal in the Software without restriction, including without limitation
#  the rights to use, copy, modify, merge, publish, distribute, sublicense,
#  and/or sell copies of the Software, and to permit persons to whom the
#  Software is furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
#  OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#  DEALINGS IN THE SOFTWARE.

from __future__ import annotations

from typing import Dict, List, Optional, TYPE_CHECKING, Any, Tuple, Union

if TYPE_CHECKING:
    from .http import Route
    from aiohttp import ClientResponse, ClientWebSocketResponse

    try:
        from requests import Response

        _ResponseType = Union[ClientResponse, Response]
    except ModuleNotFoundError:
        _ResponseType = ClientResponse

__all__ = (
    'QQException',
    'ClientException',
    'NoMoreItems',
    'GatewayNotFound',
    'HTTPException',
    'Forbidden',
    'NotFound',
    'QQServerError',
    'InvalidData',
    'InvalidArgument',
    'LoginFailure',
    'ConnectionClosed',
)


class QQException(Exception):
    """qq.py 的基本异常类，可以捕获从库引发的任何异常。"""
    pass


class ClientException(QQException):
    """当 :class:`Client` 中的操作失败时引发的异常。
    这些通常是由于用户输入而发生的异常。
    """

    pass


class NoMoreItems(QQException):
    """当异步迭代操作没有更多项目时引发的异常。"""

    pass


class GatewayNotFound(QQException):
    """找不到QQ网关时引发的异常"""

    def __init__(self):
        message = '未找到连接到 QQ 的网关。'
        super().__init__(message)


def _flatten_error_dict(d: Dict[str, Any], key: str = '') -> Dict[str, str]:
    items: List[Tuple[str, str]] = []
    for k, v in d.items():
        new_key = key + '.' + k if key else k

        if isinstance(v, dict):
            try:
                _errors: List[Dict[str, Any]] = v['_errors']
            except KeyError:
                items.extend(_flatten_error_dict(v, new_key).items())
            else:
                items.append((new_key, ' '.join(x.get('message', '') for x in _errors)))
        else:
            items.append((new_key, v))

    return dict(items)


class HTTPException(QQException):
    """HTTP 请求操作失败时引发的异常。

    Attributes
    ------------
    response: :class:`aiohttp.ClientResponse`
        失败的 HTTP 请求的响应。
        这是 :class:`aiohttp.ClientResponse` 的一个实例。
        在某些情况下，这也可能是一个 :class:`requests.Response`。
    text: :class:`str`
        错误的文本。可能是一个空字符串。
    status: :class:`int`
        HTTP 请求的状态码。
    code: :class:`int`
        失败的 QQ 特定错误代码。
    route: Optional[:class:`qq.Route`]
        HTTP 请求的路径
    """

    def __init__(
            self,
            response: _ResponseType,
            message: Optional[Union[str, Dict[str, Any]]],
            route: Optional[Route] = None
    ):
        self.route = route
        self.response: _ResponseType = response
        self.status: int = response.status  # type: ignore
        self.code: int
        self.text: str
        if isinstance(message, dict):
            self.code = message.get('code', 0)
            base = message.get('message', '')
            errors = message.get('errors')
            if errors:
                errors = _flatten_error_dict(errors)
                helpful = '\n'.join('In %s: %s' % t for t in errors.items())
                self.text = base + '\n' + helpful
            else:
                self.text = base
        else:
            self.text = message or ''
            self.code = 0

        fmt = '{0.status} {0.reason} (error code: {1})'
        if len(self.text):
            fmt += ': {2}'

        super().__init__(fmt.format(self.response, self.code, self.text))


class Forbidden(HTTPException):
    """发生状态代码 403 时引发的异常。 :exc:`HTTPException` 的子类
    """
    pass


class NotFound(HTTPException):
    """发生状态代码 404 时引发的异常。 :exc:`HTTPException` 的子类
    """
    pass


class QQServerError(HTTPException):
    """发生 500 范围状态代码时引发的异常。 :exc:`HTTPException` 的子类。
    """
    pass


class InvalidData(ClientException):
    """当库遇到来自 QQ 的未知或无效数据时引发的异常。
    """
    pass


class InvalidArgument(ClientException):
    """当函数的参数以某种方式无效时引发的异常（例如错误的值或错误的类型）。
    除了继承自 :exc:`ClientException` 和 :exc:`QQException`，这可以被认为是类似于 ``ValueError`` 和 ``TypeError`` 。
    """

    pass


class LoginFailure(ClientException):
    """当 :meth:`Client.login` 函数无法通过不正确的凭据或其他一些杂项登录时引发的异常。
    """

    pass


class ConnectionClosed(ClientException):
    """由于无法在内部处理的原因关闭网关连接时引发的异常。

    Attributes
    -----------
    code: :class:`int`
        websocket 的关闭代码。
    reason: :class:`str`
        提供了关闭的原因。
    shard_id: Optional[:class:`int`]
        如果适用，已关闭的分片 ID。
    """

    def __init__(self, socket: ClientWebSocketResponse, *, shard_id: Optional[int], code: Optional[int] = None):
        # This exception is just the same exception except
        # reconfigured to subclass ClientException for users
        self.code: int = code or socket.close_code or -1
        # aiohttp doesn't seem to consistently provide close reason
        self.reason: str = ''
        self.shard_id: Optional[int] = shard_id
        super().__init__(f'分片 ID {self.shard_id} 用 {self.code} 关闭的 WebSocket')
