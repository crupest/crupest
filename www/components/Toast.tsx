import styles from "./toast.module.css";

export default function Toast({ message }: { message: string }) {
  return <div className={styles.toast}>{message}</div>;
}
