#!/usr/bin/env dotnet run

// Read-only inspection of a BUILT assembly, with System.Reflection.Metadata only (in the
// shared framework - no packages, and the assembly is never loaded or executed).
//
//   dotnet run inspect-assembly.cs -- <x.dll>                        references, resources, types, methods
//   dotnet run inspect-assembly.cs -- <x.dll> <Ns.Type> <Method>     IL of every overload of that method
//
// The IL listing resolves call/field/type operands to names and branch operands to labels.
// It does not print exception-handler regions (see MethodBodyBlock.ExceptionRegions).

using System.Reflection;
using System.Reflection.Emit;
using System.Reflection.Metadata;
using System.Reflection.Metadata.Ecma335;
using System.Reflection.PortableExecutable;

using var pe = new PEReader(File.OpenRead(args[0]));
if (!pe.HasMetadata) { Console.WriteLine("not a managed assembly"); return 1; }
var md = pe.GetMetadataReader();

if (args.Length < 3)
{
    if (md.IsAssembly) Console.WriteLine($"assembly {md.GetAssemblyDefinition().GetAssemblyName()}");
    foreach (var h in md.AssemblyReferences) Console.WriteLine($"  ref      {md.GetAssemblyReference(h).GetAssemblyName()}");
    foreach (var h in md.ManifestResources) Console.WriteLine($"  resource {md.GetString(md.GetManifestResource(h).Name)}");
    foreach (var th in md.TypeDefinitions)
    {
        var type = md.GetTypeDefinition(th);
        Console.WriteLine($"  type     {FullName(md, type)}  [{type.Attributes & TypeAttributes.VisibilityMask}]");
        foreach (var mh in type.GetMethods())
            Console.WriteLine($"    method {md.GetString(md.GetMethodDefinition(mh).Name)}");
    }
    return 0;
}

var opcodes = typeof(OpCodes).GetFields(BindingFlags.Public | BindingFlags.Static)
    .Select(f => (OpCode)f.GetValue(null)!)
    .DistinctBy(o => o.Value)   // guard: a duplicate value must not throw
    .ToDictionary(o => (ushort)o.Value);

var found = 0;
foreach (var th in md.TypeDefinitions)
{
    var type = md.GetTypeDefinition(th);
    if (FullName(md, type) != args[1]) continue;
    foreach (var mh in type.GetMethods())
    {
        var method = md.GetMethodDefinition(mh);
        if (md.GetString(method.Name) != args[2] || method.RelativeVirtualAddress == 0) continue;
        found++;
        var body = pe.GetMethodBody(method.RelativeVirtualAddress);
        Console.WriteLine($"// {args[1]}::{args[2]} (token 0x{MetadataTokens.GetToken(mh):x8}), maxstack {body.MaxStack}, localsinit {body.LocalVariablesInitialized}");
        var il = body.GetILReader();
        while (il.RemainingBytes > 0)
        {
            var offset = il.Offset;
            ushort code = il.ReadByte();
            if (code == 0xFE) code = (ushort)(0xFE00 | il.ReadByte());   // two-byte opcodes
            var op = opcodes[code];
            Console.WriteLine($"  IL_{offset:x4}: {op.Name,-12} {Operand(ref il, op.OperandType, md)}");
        }
    }
}
if (found == 0) { Console.Error.WriteLine($"no method body {args[1]}::{args[2]}"); return 1; }
return 0;

static string FullName(MetadataReader md, TypeDefinition t)
{
    var name = md.GetString(t.Name);
    if (t.GetDeclaringType() is { IsNil: false } outer) return $"{FullName(md, md.GetTypeDefinition(outer))}+{name}";
    var ns = md.GetString(t.Namespace);
    return ns.Length == 0 ? name : $"{ns}.{name}";
}

static string Operand(ref BlobReader il, OperandType kind, MetadataReader md)
{
    switch (kind)
    {
        case OperandType.InlineNone: return "";
        case OperandType.ShortInlineBrTarget: { int delta = il.ReadSByte(); return $"IL_{il.Offset + delta:x4}"; }
        case OperandType.InlineBrTarget: { var delta = il.ReadInt32(); return $"IL_{il.Offset + delta:x4}"; }
        case OperandType.ShortInlineI: return il.ReadSByte().ToString();
        case OperandType.ShortInlineVar: return il.ReadByte().ToString();
        case OperandType.InlineVar: return il.ReadUInt16().ToString();
        case OperandType.InlineI: return il.ReadInt32().ToString();
        case OperandType.InlineI8: return il.ReadInt64().ToString();
        case OperandType.ShortInlineR: return il.ReadSingle().ToString("R");
        case OperandType.InlineR: return il.ReadDouble().ToString("R");
        case OperandType.InlineString:
            return $"\"{md.GetUserString(MetadataTokens.UserStringHandle(il.ReadInt32() & 0x00FFFFFF))}\"";
        case OperandType.InlineSwitch:
        {
            var targets = new int[il.ReadInt32()];
            for (var i = 0; i < targets.Length; i++) targets[i] = il.ReadInt32();
            var end = il.Offset;   // switch deltas are relative to the end of the instruction
            return string.Join(", ", targets.Select(d => $"IL_{end + d:x4}"));
        }
        default:   // InlineMethod, InlineField, InlineType, InlineTok, InlineSig: a 4-byte token
            return Describe(md, MetadataTokens.EntityHandle(il.ReadInt32()));
    }
}

static string Describe(MetadataReader md, EntityHandle h) => h.Kind switch
{
    HandleKind.MethodDefinition => md.GetString(md.GetMethodDefinition((MethodDefinitionHandle)h).Name),
    HandleKind.MemberReference => md.GetString(md.GetMemberReference((MemberReferenceHandle)h).Name),
    HandleKind.FieldDefinition => md.GetString(md.GetFieldDefinition((FieldDefinitionHandle)h).Name),
    HandleKind.TypeDefinition => FullName(md, md.GetTypeDefinition((TypeDefinitionHandle)h)),
    HandleKind.TypeReference => md.GetString(md.GetTypeReference((TypeReferenceHandle)h).Name),
    _ => $"{h.Kind} 0x{MetadataTokens.GetToken(h):x8}",
};
