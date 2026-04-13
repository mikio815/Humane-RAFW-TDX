# Humane Intel TDX Remote Attestation Framework for baremetal environment (Humane-RAFW-TDX)
本リポジトリは、Intel TDXのDCAPベースのRemote Attestation（RA）を、検証用付属情報（コラテラル）をPCCSというキャッシュサーバにキャッシュさせながらの完全な公式想定の形で、「人道的な」（Humane）難易度で手軽に実現する事のできるRAフレームワーク（RAFW）のコードやリソースを格納しています。  
ただし、本リポジトリはあくまでもベアメタルマシン上でTDX環境を構築し、その上でTDを動作させてそれに対するRAを実施するシナリオを想定しています。特に、AzureにおけるTDX VMインスタンスにおけるAttestationとは基本的に互換性が無い点に注意してください。

* [公式のTDX RAサンプル](https://github.com/intel/confidential-computing.tee.dcap/blob/DCAP_1.25/QuoteGeneration/quote_wrapper/tdx_attest/test_tdx_attest.c)は、それこそ同じRA基盤を持つIntel SGXと比較すると、劇的に改善されました。しかし、この検証側サンプルコードはこれとは別のプログラムとして提供されており、エンドツーエンドの形にはなっていません。