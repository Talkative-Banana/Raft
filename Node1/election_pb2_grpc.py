# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

import election_pb2 as election__pb2


class ElectionStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.ServeClient = channel.unary_unary(
                '/election.Election/ServeClient',
                request_serializer=election__pb2.ServeClientArgs.SerializeToString,
                response_deserializer=election__pb2.ServeClientReply.FromString,
                )
        self.RequestVote = channel.unary_unary(
                '/election.Election/RequestVote',
                request_serializer=election__pb2.RequestVoteRequest.SerializeToString,
                response_deserializer=election__pb2.RequestVoteResponse.FromString,
                )
        self.AppendEntries = channel.unary_unary(
                '/election.Election/AppendEntries',
                request_serializer=election__pb2.RequestAppendEntries.SerializeToString,
                response_deserializer=election__pb2.ResponseAppendEntries.FromString,
                )


class ElectionServicer(object):
    """Missing associated documentation comment in .proto file."""

    def ServeClient(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def RequestVote(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def AppendEntries(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_ElectionServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'ServeClient': grpc.unary_unary_rpc_method_handler(
                    servicer.ServeClient,
                    request_deserializer=election__pb2.ServeClientArgs.FromString,
                    response_serializer=election__pb2.ServeClientReply.SerializeToString,
            ),
            'RequestVote': grpc.unary_unary_rpc_method_handler(
                    servicer.RequestVote,
                    request_deserializer=election__pb2.RequestVoteRequest.FromString,
                    response_serializer=election__pb2.RequestVoteResponse.SerializeToString,
            ),
            'AppendEntries': grpc.unary_unary_rpc_method_handler(
                    servicer.AppendEntries,
                    request_deserializer=election__pb2.RequestAppendEntries.FromString,
                    response_serializer=election__pb2.ResponseAppendEntries.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'election.Election', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class Election(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def ServeClient(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/election.Election/ServeClient',
            election__pb2.ServeClientArgs.SerializeToString,
            election__pb2.ServeClientReply.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def RequestVote(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/election.Election/RequestVote',
            election__pb2.RequestVoteRequest.SerializeToString,
            election__pb2.RequestVoteResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def AppendEntries(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/election.Election/AppendEntries',
            election__pb2.RequestAppendEntries.SerializeToString,
            election__pb2.ResponseAppendEntries.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)
