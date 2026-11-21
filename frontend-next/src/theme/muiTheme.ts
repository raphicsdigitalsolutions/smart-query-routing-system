'use client';

import { createTheme } from '@mui/material/styles';

/**
 * MUI is retained for tables, dialogs and structured forms. These overrides
 * align it with the Tailwind design tokens so both systems read as one product.
 */
export const muiTheme = createTheme({
  cssVariables: false,
  palette: {
    mode: 'light',
    primary: { main: '#102A43', light: '#234262', dark: '#0A1B2C', contrastText: '#ffffff' },
    secondary: { main: '#0D9488', light: '#14B8A6', dark: '#0B7A72', contrastText: '#ffffff' },
    success: { main: '#0F766E', light: '#D3F4EE' },
    warning: { main: '#B45309', light: '#FEF3C7' },
    error: { main: '#BE123C', light: '#FFE4E6' },
    info: { main: '#0369A1', light: '#E0F2FE' },
    background: { default: '#F5F7FA', paper: '#ffffff' },
    text: { primary: '#102A43', secondary: '#64748B' },
    divider: '#E6EBF1',
  },
  shape: { borderRadius: 10 },
  typography: {
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    fontSize: 14,
    button: { textTransform: 'none', fontWeight: 600 },
    h6: { fontWeight: 650 },
  },
  components: {
    MuiTextField: {
      defaultProps: { size: 'small', variant: 'outlined' },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          borderRadius: 10,
          backgroundColor: '#ffffff',
          fontSize: 14,
          '& fieldset': { borderColor: '#CBD5E1', transition: 'border-color 140ms ease' },
          '&:hover fieldset': { borderColor: '#94A3B8' },
          '&.Mui-focused fieldset': {
            borderColor: '#0D9488',
            borderWidth: 1.5,
            boxShadow: '0 0 0 3px rgba(13, 148, 136, 0.12)',
          },
        },
        input: { padding: '11px 14px' },
      },
    },
    MuiInputLabel: {
      styleOverrides: {
        root: { color: '#64748B', fontSize: 14, '&.Mui-focused': { color: '#0D9488' } },
      },
    },
    MuiFormHelperText: {
      styleOverrides: { root: { fontSize: 12, marginLeft: 2 } },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: { borderRadius: 10, paddingInline: 16, minHeight: 38, fontWeight: 600, boxShadow: 'none' },
        sizeSmall: { minHeight: 32, paddingInline: 12 },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: { borderRadius: 16, boxShadow: '0 18px 45px -18px rgba(16, 42, 67, 0.32)' },
        backdrop: { backgroundColor: 'rgba(10, 27, 44, 0.5)', backdropFilter: 'blur(2px)' },
      },
    },
    MuiDialogTitle: {
      styleOverrides: { root: { fontWeight: 650, fontSize: '1.125rem', padding: '20px 24px 8px' } },
    },
    MuiDialogContent: {
      styleOverrides: { root: { padding: '8px 24px 16px' } },
    },
    MuiDialogActions: {
      styleOverrides: { root: { padding: '12px 24px 20px', gap: 8 } },
    },
    MuiTableCell: {
      styleOverrides: {
        root: { borderColor: '#EDF1F5', padding: '10px 14px', fontSize: 13.5 },
        head: {
          fontWeight: 700,
          color: '#64748B',
          fontSize: '11px',
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          backgroundColor: '#F8FAFC',
        },
      },
    },
    MuiTableRow: {
      styleOverrides: { root: { '&:hover': { backgroundColor: '#F8FAFC' } } },
    },
    MuiMenu: {
      styleOverrides: {
        paper: { borderRadius: 12, marginTop: 6, boxShadow: '0 12px 32px rgba(16, 42, 67, 0.16)' },
      },
    },
    MuiCheckbox: {
      styleOverrides: {
        root: { color: '#94A3B8', '&.Mui-checked': { color: '#0D9488' } },
      },
    },
  },
});
