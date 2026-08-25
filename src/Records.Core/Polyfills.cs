#if !NET
// `record` and `init` accessors need this attribute; .NET Framework / netstandard2.0 do not ship it.
namespace System.Runtime.CompilerServices
{
    internal static class IsExternalInit { }
}
#endif
