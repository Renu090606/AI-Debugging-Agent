import Editor from "@monaco-editor/react";

function CodeEditor({ value, onChange, theme }) {
  const handleMount = (editor) => {
    editor.focus();
  };

  const monacoTheme = theme === "light" ? "vs" : "vs-dark";

  return (
    <Editor
      height="100%"
      defaultLanguage="python"
      theme={monacoTheme}
      value={value}
      onChange={(val) => onChange(val || "")}
      onMount={handleMount}
      options={{
        minimap: { enabled: false },
        fontSize: 14,
        lineNumbers: "on",
        scrollBeyondLastLine: false,
        automaticLayout: true,
        wordWrap: "on",
        padding: { top: 8 },
      }}
      loading={
        <div style={{ padding: 20, color: "#9d9d9d", fontFamily: "monospace" }}>
          Loading editor...
        </div>
      }
    />
  );
}

export default CodeEditor;
